import logging

from core.celery_app import celery_app
from messaging.constants import UpdateModelFamilies

from auraflux_core.core.schemas.clients import ProviderConfig

from .models import ModelProvider, ModelFamilies
from .utils import measure_model_provider_connection

logger = logging.getLogger(__name__)


@celery_app.task(name=UpdateModelFamilies.name, ignore_result=True)
def update_model_families(event_type: str, payload: dict):
    task_id = update_model_families.request.id
    provider_id = payload.get('provider_id', '')
    logger.info("Task %s: Starting model family update for provider %s.", task_id, provider_id)

    model_provider = ModelProvider.objects.get(id=provider_id)
    available_models = measure_model_provider_connection(
        provider_id=str(model_provider.id),
        provider_type=model_provider.provider_type,
        api_key=model_provider.get_api_key(),
        model_class=ModelProvider
    )

    if available_models is None:
        return

    for model in available_models.get('models', []):
        family, created = ModelFamilies.objects.get_or_create(
            name=model['name'],
            display_name=model['display_name'],
            description=model['description'],
            input_token_limit=model['input_token_limit'],
            output_token_limit=model['output_token_limit']
        )

        if not model_provider.supported_families.filter(id=family.id).exists():
            model_provider.supported_families.add(family)
