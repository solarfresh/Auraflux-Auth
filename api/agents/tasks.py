import logging

from core.celery_app import celery_app
from messaging.constants import AgentRequest, UpdateModelFamilies
from messaging.tasks import publish_event

from .models import ModelFamilies, ModelProvider
from .utils import measure_model_provider_connection, get_agent_response

logger = logging.getLogger(__name__)

@celery_app.task(name=AgentRequest.name, ignore_result=True)
def handle_agent_request(event_type: str, payload: dict):
    """
    Generic consumer task for handling agent requests.

    This task is designed to be flexible and reusable for any agent defined in the system. It takes in a payload that specifies which agent to execute, the input data for that agent, and optionally the format of the output and the next event to publish.
    Args:
        payload: A dictionary containing the necessary information to execute the agent, including:
            - agent_name: The name of the agent instance.
            - agent_role: The role of the agent (e.g., 'assistant', 'researcher
            - system_prompt: The system prompt to initialize the agent with.
            - llm_parameters: Parameters for configuring the LLM.
            - agent_input_data: Data to be used for composing the prompt.
            - prompt_template: Template string for the prompt, with placeholders for variables.
            - template_variables: Mapping of variable names to their corresponding values for prompt rendering.
            - prompt_text: Direct prompt text to send to the agent.
            - tool_args_map: Optional mapping of tool names to their arguments for dynamic tool configuration.
            - next_event_type: Optional event type to publish after obtaining the agent's response.
            - next_event_queue: Optional queue name for the next event.
            - output_format: The desired format of the agent's output ('json' or 'text').
    """

    task_id = handle_agent_request.request.id
    agent_role = payload.get('agent_role', 'unknown')
    next_event_type = payload.get('next_event_type', None)
    next_event_payload = payload.get('next_event_payload', {})
    next_event_queue = payload.get('next_event_queue', None)

    logger.info("Task %s: Handling agent request for agent role %s.", task_id, agent_role)

    try:
        agent_output = get_agent_response(**payload)
    except Exception:
        logger.critical("Task %s: Agent execution failed for agent role %s.", task_id, agent_role)
        return

    if next_event_type and next_event_type is not None:
        next_event_payload.update({
            'agent_output': agent_output
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
