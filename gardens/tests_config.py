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

    def test_production_compose_database_uses_env_file_not_hardcoded_password(self):
        compose = (Path(settings.BASE_DIR) / 'docker-compose.prod.yml').read_text()

        self.assertIn('db:\n    image: postgres:18\n    env_file: .env.prod', compose)
        self.assertIn('pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB', compose)
        self.assertNotIn('POSTGRES_PASSWORD: postgres', compose)
