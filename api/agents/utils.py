import logging
from typing import Any, Dict, List
from uuid import uuid4

from asgiref.sync import async_to_sync
from auraflux_core.core.clients.client_manager import ClientManager
from auraflux_core.core.schemas.clients import ClientConfig, ProviderConfig

logger = logging.getLogger(__name__)


def get_provider_configs() -> List:
    from agents.models import ModelProvider

    provider_configs = []
    providers = ModelProvider.objects.all()
    for provider in providers:
        provider_config = ProviderConfig(
            id=str(provider.id),
            type=provider.provider_type,
            base_url=provider.base_url,
            api_key=provider.get_api_key(),
        )
        provider_configs.append(provider_config)

    return provider_configs

def measure_model_provider_connection(provider_type: str, api_key: str, provider_id: str = '', model_class=None) -> Dict[str, Any] | None:
    if model_class is None:
        logger.warning("Model class not provided for measuring model provider connection. Defaulting to ModelProvider.")
        return

    if provider_id:
        model_provider = model_class.objects.get(id=provider_id)
        provider_config = [ProviderConfig(
            id=provider_id,
            provider_type=provider_type.upper(),
            api_key=model_provider.get_api_key()
        )]
    else:
        provider_id = str(uuid4())
        provider_config = [ProviderConfig(id=provider_id, name='test', provider_type=provider_type, api_key=api_key)]

    client_config = ClientConfig(models=provider_config)
    client_manager = ClientManager(client_config)
    async_to_sync(client_manager.instantiate_handlers)()

    return client_manager.get_available_models(provider_id=provider_id)
