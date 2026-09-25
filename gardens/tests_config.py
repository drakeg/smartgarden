from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


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
