from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

import smartgarden.settings as project_settings


class DockerConfigurationTests(SimpleTestCase):
    def test_development_compose_uses_app_port_from_env(self):
        compose = (Path(settings.BASE_DIR) / "docker-compose.yml").read_text()
        self.assertIn('${APP_PORT:-8000}:8000', compose)

    def test_production_compose_uses_app_port_from_env(self):
        compose = (Path(settings.BASE_DIR) / "docker-compose.prod.yml").read_text()
        self.assertIn('${APP_PORT:-80}:80', compose)

    def test_environment_examples_document_app_port(self):
        dev_env = (Path(settings.BASE_DIR) / ".env.example").read_text()
        prod_env = (Path(settings.BASE_DIR) / ".env.prod.example").read_text()
        self.assertIn("APP_PORT=8000", dev_env)
        self.assertIn("APP_PORT=80", prod_env)


    def test_celery_installs_redis_transport(self):
        requirements = (Path(settings.BASE_DIR) / "requirements.txt").read_text()
        self.assertIn("celery[redis]", requirements)

    def test_async_email_profile_is_available_in_compose(self):
        dev_compose = (Path(settings.BASE_DIR) / "docker-compose.yml").read_text()
        prod_compose = (Path(settings.BASE_DIR) / "docker-compose.prod.yml").read_text()

        for compose in (dev_compose, prod_compose):
            self.assertIn('profiles: ["async-email"]', compose)
            self.assertIn("celery-worker:", compose)
            self.assertIn("redis:", compose)
            self.assertIn("CELERY_BROKER_URL=", compose)


    def test_compose_uses_redis_8_consistently(self):
        dev_compose = (Path(settings.BASE_DIR) / "docker-compose.yml").read_text()
        prod_compose = (Path(settings.BASE_DIR) / "docker-compose.prod.yml").read_text()

        self.assertIn("image: redis:8-alpine", dev_compose)
        self.assertIn("image: redis:8-alpine", prod_compose)
        self.assertNotIn("image: redis:7-alpine", dev_compose)
        self.assertNotIn("image: redis:7-alpine", prod_compose)


class ProductionDatabaseConfigurationTests(SimpleTestCase):
    def test_production_postgres_config_uses_postgres_environment(self):
        env = {
            'POSTGRES_DB': 'garden_prod',
            'POSTGRES_USER': 'garden_user',
            'POSTGRES_PASSWORD': 'secret-pass',
            'POSTGRES_HOST': 'db.internal',
            'POSTGRES_PORT': '5544',
        }
        with patch.object(project_settings, 'DEBUG', False), patch.dict(
            'os.environ', env, clear=True,
        ):
            config = project_settings._database_config_from_env()

        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['NAME'], 'garden_prod')
        self.assertEqual(config['USER'], 'garden_user')
        self.assertEqual(config['PASSWORD'], 'secret-pass')
        self.assertEqual(config['HOST'], 'db.internal')
        self.assertEqual(config['PORT'], '5544')
        self.assertEqual(config['CONN_MAX_AGE'], 600)

    def test_database_url_overrides_postgres_environment(self):
        env = {
            'DATABASE_URL': 'postgres://urluser:urlpass@urlhost:5433/urldb',
            'POSTGRES_PASSWORD': 'ignored',
        }
        with patch.object(project_settings, 'DEBUG', False), patch.dict(
            'os.environ', env, clear=True,
        ):
            config = project_settings._database_config_from_env()

        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['NAME'], 'urldb')
        self.assertEqual(config['USER'], 'urluser')
        self.assertEqual(config['HOST'], 'urlhost')
        self.assertEqual(str(config['PORT']), '5433')

    def test_production_database_requires_password_without_database_url(self):
        with patch.object(project_settings, 'DEBUG', False), patch.dict(
            'os.environ', {}, clear=True,
        ):
            with self.assertRaises(ImproperlyConfigured):
                project_settings._database_config_from_env()

    def test_development_still_defaults_to_sqlite(self):
        with patch.object(project_settings, 'DEBUG', True), patch.dict(
            'os.environ', {}, clear=True,
        ):
            config = project_settings._database_config_from_env()

        self.assertEqual(config['ENGINE'], 'django.db.backends.sqlite3')

    def test_production_web_waits_for_database_health_and_uses_readiness(self):
        compose = (Path(settings.BASE_DIR) / 'docker-compose.prod.yml').read_text()

        self.assertIn('db:\n        condition: service_healthy', compose)
        self.assertIn('curl -f http://localhost:8000/ready/ || exit 1', compose)
        self.assertNotIn('curl -f http://localhost:8000/health/ || exit 1', compose)

    def test_production_compose_database_uses_env_file_not_hardcoded_password(self):
        compose = (Path(settings.BASE_DIR) / 'docker-compose.prod.yml').read_text()

        self.assertIn('db:\n    image: postgres:18\n    env_file: .env.prod', compose)
        self.assertIn('test: ["CMD", "pg_isready"]', compose)
        self.assertNotIn('POSTGRES_PASSWORD: postgres', compose)


class ProductionRuntimeConfigurationTests(SimpleTestCase):
    def test_production_web_uses_entrypoint_once_and_execs_gunicorn_directly(self):
        compose = (Path(settings.BASE_DIR) / 'docker-compose.prod.yml').read_text()
        entrypoint = (Path(settings.BASE_DIR) / 'entrypoint.sh').read_text()

        self.assertIn('command:\n      - gunicorn', compose)
        self.assertNotIn('sh -c "python manage.py migrate', compose)
        self.assertEqual(compose.count('python manage.py migrate --noinput'), 0)
        self.assertEqual(entrypoint.count('python manage.py migrate --noinput'), 1)
        self.assertIn('exec "$@"', entrypoint)

    def test_production_web_has_graceful_shutdown_window(self):
        compose = (Path(settings.BASE_DIR) / 'docker-compose.prod.yml').read_text()

        self.assertIn('stop_grace_period: 30s', compose)
        self.assertIn('- --graceful-timeout\n      - "25"', compose)
        self.assertIn('- --timeout\n      - "30"', compose)


class ReverseProxyConfigurationTests(SimpleTestCase):
    def test_nginx_preserves_upstream_forwarded_proto_with_scheme_fallback(self):
        nginx = (Path(settings.BASE_DIR) / 'deploy/nginx.prod.conf').read_text()

        self.assertIn('map $http_x_forwarded_proto $smartgarden_forwarded_proto', nginx)
        self.assertIn('default $http_x_forwarded_proto;', nginx)
        self.assertIn('"" $scheme;', nginx)
        self.assertIn(
            'proxy_set_header X-Forwarded-Proto $smartgarden_forwarded_proto;',
            nginx,
        )

    def test_production_env_documents_explicit_proxy_trust(self):
        env = (Path(settings.BASE_DIR) / '.env.prod.example').read_text()
        settings_source = (Path(settings.BASE_DIR) / 'smartgarden/settings.py').read_text()

        self.assertIn('TRUST_X_FORWARDED_PROTO=True', env)
        self.assertIn('SECURE_SSL_REDIRECT=True', env)
        self.assertIn("'TRUST_X_FORWARDED_PROTO', 'False'", settings_source)
        self.assertIn(
            "SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')",
            settings_source,
        )
