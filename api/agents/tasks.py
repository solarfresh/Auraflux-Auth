import json
import logging

from core.celery_app import celery_app
from messaging.constants import (AgentRequest, EmbeddingRequest,
                                 UpdateModelFamilies)
from messaging.tasks import publish_event
from services.semaphore import acquire_concurrency_slot

from .models import ModelFamilies, ModelProvider
from .utils import (get_agent_response, get_embedding_response,
                    measure_model_provider_connection)

logger = logging.getLogger(__name__)

@celery_app.task(name=AgentRequest.name, ignore_result=True)
def handle_agent_request(event_type: str, payload: dict):
    """
    Generic consumer task for handling agent requests.

    Args:
        event_type: The type of event being handled.
        payload: A dictionary containing execution parameters, aligned with the unified agent contract:
            - type: The agent type identifier.
            - config: Agent configuration dictionary (e.g., system_prompt, llm_parameters).
            - payload: Execution payload including agent_input_data, prompt_template, etc.
            - next_event_type: Optional event to publish after agent execution.
            - next_event_payload: Base dictionary for the next event payload.
            - next_event_queue: Queue name for the next event.
    """

    task_id = handle_agent_request.request.id
    provider_id = payload.get('provider_id', None)
    agent_role = payload.get('agent_role', 'unknown')
    next_event_type = payload.get('next_event_type', None)
    next_event_payload = payload.get('next_event_payload', {})
    next_event_queue = payload.get('next_event_queue', None)

    if provider_id is None:
        raise ValueError("Provider ID is required in the payload.")

    logger.info("Task %s: Handling agent request for agent role %s.", task_id, agent_role)

    try:
        with acquire_concurrency_slot(key_prefix=provider_id, max_concurrency=1, timeout=60):
            agent_output = get_agent_response(**payload)
    except Exception:
        logger.critical("Task %s: Agent execution failed for agent role %s.", task_id, agent_role)
        agent_output = None

    if next_event_type and next_event_type is not None:
        next_event_payload.update({
            'agent_output': agent_output
        })
        publish_event.delay(
            event_type=next_event_type,
            payload=next_event_payload,
            queue=next_event_queue if next_event_queue else 'default'
        )

@celery_app.task(name=EmbeddingRequest.name, ignore_result=True)
def handle_embedding_request(event_type: str, payload: dict):
    """
    Generic consumer task for handling vector embedding requests.

    Args:
        event_type: The type of event being handled.
        payload: A dictionary containing execution parameters, aligned with the unified embedding contract:
            - type: The embedding type identifier.
            - config: Embedding configuration dictionary (e.g., model, parameters).
            - payload: Execution payload including input_text, etc.
            - next_event_type: Optional event to publish after generating embeddings.
            - next_event_payload: Base dictionary for the next event payload.
            - next_event_queue: Queue name for the next event.
    """
    task_id = handle_embedding_request.request.id
    provider_id = payload.get('provider_id', None)
    embedding_name = payload.get('embedding_name', 'unknown')
    next_event_type = payload.get('next_event_type', None)
    next_event_payload = payload.get('next_event_payload', {})
    next_event_queue = payload.get('next_event_queue', None)

    if provider_id is None:
        raise ValueError("Provider ID is required in the payload.")

    logger.info("Task %s: Handling embedding request for %s.", task_id, embedding_name)

    try:
        with acquire_concurrency_slot(key_prefix=provider_id, max_concurrency=1, timeout=60):
            embedding_output = get_embedding_response(**payload)
    except Exception:
        logger.critical("Task %s: Embedding execution failed for %s.", task_id, embedding_name)
        embedding_output = None

    if next_event_type:
        next_event_payload.update({
            'embedding_output': embedding_output
        })
        publish_event.delay(
            event_type=next_event_type,
            payload=next_event_payload,
            queue=next_event_queue if next_event_queue else 'default'
        )

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
