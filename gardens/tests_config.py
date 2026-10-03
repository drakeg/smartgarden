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


class DatabaseBackupRestoreConfigurationTests(SimpleTestCase):
    def test_backup_script_uses_custom_format_atomic_output_and_env_file(self):
        script = (Path(settings.BASE_DIR) / 'scripts/backup_postgres.sh').read_text()

        self.assertIn('docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db', script)
        self.assertIn('pg_dump', script)
        self.assertIn('--format=custom', script)
        self.assertIn('--no-owner', script)
        self.assertIn('--no-privileges', script)
        self.assertIn('backup_path="$BACKUP_DIR/smartgarden-$timestamp.dump"', script)
        self.assertIn('tmp_path="$backup_path.tmp"', script)
        self.assertIn('mv "$tmp_path" "$backup_path"', script)
        self.assertNotIn('POSTGRES_PASSWORD=', script)

    def test_restore_script_requires_confirmation_and_cleans_existing_objects(self):
        script = (Path(settings.BASE_DIR) / 'scripts/restore_postgres.sh').read_text()

        self.assertIn('RESTORE_CONFIRM', script)
        self.assertIn('!= "YES"', script)
        self.assertIn('pg_restore', script)
        self.assertIn('--clean', script)
        self.assertIn('--if-exists', script)
        self.assertIn('--exit-on-error', script)
        self.assertIn('--no-owner', script)
        self.assertIn('--no-privileges', script)
        self.assertNotIn('POSTGRES_PASSWORD=', script)

    def test_generated_database_backups_are_gitignored(self):
        gitignore = (Path(settings.BASE_DIR) / '.gitignore').read_text()

        self.assertIn('backups/', gitignore)
        self.assertIn('*.dump', gitignore)


class PersistentMediaConfigurationTests(SimpleTestCase):
    def test_production_media_uses_shared_persistent_volume(self):
        compose = (Path(settings.BASE_DIR) / 'docker-compose.prod.yml').read_text()

        self.assertIn('mediafiles:/app/media', compose)
        self.assertIn('mediafiles:/usr/share/nginx/html/media:ro', compose)
        self.assertIn('mediafiles:', compose)

    def test_nginx_serves_persistent_media_with_nosniff(self):
        nginx = (Path(settings.BASE_DIR) / 'deploy/nginx.prod.conf').read_text()

        self.assertIn('location /media/', nginx)
        self.assertIn('alias /usr/share/nginx/html/media/;', nginx)
        self.assertIn('add_header X-Content-Type-Options nosniff always;', nginx)

    def test_media_backup_and_restore_scripts_use_media_volume(self):
        backup = (Path(settings.BASE_DIR) / 'scripts/backup_media.sh').read_text()
        restore = (Path(settings.BASE_DIR) / 'scripts/restore_media.sh').read_text()

        self.assertIn('-C /app/media -czf - .', backup)
        self.assertIn('smartgarden-media-$timestamp.tar.gz', backup)
        self.assertIn('tmp_path="$backup_path.tmp"', backup)
        self.assertIn('RESTORE_CONFIRM', restore)
        self.assertIn('-C /app/media -xzf -', restore)


class BackupVerificationRetentionTests(SimpleTestCase):
    def test_individual_backup_scripts_support_shared_timestamp_and_verify_output(self):
        db = (Path(settings.BASE_DIR) / 'scripts/backup_postgres.sh').read_text()
        media = (Path(settings.BASE_DIR) / 'scripts/backup_media.sh').read_text()

        self.assertIn('BACKUP_TIMESTAMP', db)
        self.assertIn('BACKUP_TIMESTAMP', media)
        self.assertIn('pg_restore --list', db)
        self.assertIn('-tzf - < "$tmp_path"', media)

    def test_backup_all_uses_one_timestamp_and_verifies_the_pair(self):
        script = (Path(settings.BASE_DIR) / 'scripts/backup_all.sh').read_text()

        self.assertIn('export BACKUP_TIMESTAMP="$timestamp"', script)
        self.assertIn('sh scripts/backup_postgres.sh', script)
        self.assertIn('sh scripts/backup_media.sh', script)
        self.assertIn('sh scripts/verify_backup_set.sh "$db_backup" "$media_backup"', script)

    def test_backup_set_verifier_checks_database_and_media_formats(self):
        script = (Path(settings.BASE_DIR) / 'scripts/verify_backup_set.sh').read_text()

        self.assertIn('pg_restore --list', script)
        self.assertIn('-tzf - < "$media_backup"', script)
        self.assertIn('Backup artifact is missing or empty', script)

    def test_prune_backups_defaults_to_dry_run_and_matches_only_smartgarden_artifacts(self):
        script = (Path(settings.BASE_DIR) / 'scripts/prune_backups.sh').read_text()

        self.assertIn('RETENTION_DAYS="${RETENTION_DAYS:-30}"', script)
        self.assertIn('PRUNE_CONFIRM', script)
        self.assertIn('!= "YES"', script)
        self.assertIn('smartgarden-????????T??????Z.dump', script)
        self.assertIn('smartgarden-media-????????T??????Z.tar.gz', script)
        self.assertIn('Dry run:', script)
        self.assertIn('-exec rm -f -- {} +', script)
