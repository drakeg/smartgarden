import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartgarden.settings")

app = Celery("smartgarden")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
