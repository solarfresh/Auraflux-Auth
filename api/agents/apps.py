import logging

from celery.signals import worker_process_init
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AgentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agents'
    label = 'agents'

    def ready(self):
        """
        Initialize AurafluxEngineSingleton on application startup.
        """
        from agents.models import ModelProvider
        from services.engine import AurafluxEngineSingleton

        try:
            providers = list(ModelProvider.objects.all())
            AurafluxEngineSingleton().initialize(providers=providers)
            logger.info("AurafluxEngine initialized on app ready.")
        except Exception as e:
            logger.error(f"Error initializing AurafluxEngine: {e}")


@worker_process_init.connect
def initialize_resources(sender=None, **kwargs):
    """Initializes resources for Celery worker processes."""
    from agents.models import ModelProvider
    from services.engine import AurafluxEngineSingleton
    try:
        providers = list(ModelProvider.objects.all())
        AurafluxEngineSingleton().initialize(providers=providers)
    except Exception as e:
        logger.error(f"Error initializing AurafluxEngine in Celery worker: {e}")
