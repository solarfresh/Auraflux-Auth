import logging

from asgiref.sync import async_to_sync, sync_to_async
from auraflux_core.core.clients.client_manager import ClientManager
from auraflux_core.core.schemas.clients import ClientConfig
from celery.signals import worker_process_init
from django.apps import AppConfig

from .utils import get_provider_configs, set_global_client_manager

logger = logging.getLogger(__name__)


class AgentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agents'
    label = 'agents'


async def _async_initialize_client_manager():
    """
    This method is called after the application is ready and migrations have run.
    It reads settings, converts them to Pydantic models, and initializes the ClientManager.
    """

    # Initialize and set global ClientManager
    provider_configs = await sync_to_async(get_provider_configs)()
    if provider_configs:
        try:
            client_config = ClientConfig(providers=provider_configs, initialize_mode='run_forever')
            client_manager = ClientManager(client_config)
            await client_manager.initialize()
            set_global_client_manager(client_manager)
            # AgentsConfig.client_manager = client_manager
            logger.info("Global ClientManager initialized with %d providers.", len(provider_configs))
        except Exception as e:
            logger.critical(f"Failed to initialize global ClientManager: {e}")


@worker_process_init.connect
def initialize_resources(sender=None, **kwargs):
    """Initializes resources for Celery worker processes."""
    async_to_sync(_async_initialize_client_manager)()
