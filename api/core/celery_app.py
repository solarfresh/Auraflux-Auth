import os

from celery import Celery
from django.apps import apps
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

celery_app = Celery(
    settings.CELERY['name'],
    namespace=settings.CELERY['namespace'],
    broker=settings.CELERY['broker'],
    backend=settings.CELERY['backend'],
    broker_connection_retry_on_startup=True,
    celery_task_track_started=True
)

celery_app.config_from_object('django.conf:settings')
celery_app.autodiscover_tasks(list(apps.app_configs.keys()))
