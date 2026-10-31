import logging
import time
from threading import Lock
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import uuid4

from asgiref.sync import async_to_sync
from auraflux_core.core.clients.client_manager import ClientManager
from auraflux_core.core.schemas.agents import AgentConfig
from auraflux_core.core.schemas.clients import ClientConfig, ProviderConfig
from auraflux_core.core.schemas.embeddings import EmbeddingConfig
from auraflux_core.core.schemas.messages import Message
from auraflux_core.embeddings import EMBEDDING_REGISTRY
from services.engine import AurafluxEngineSingleton
from services.exceptions import EngineInitializationError

logger = logging.getLogger(__name__)

_INIT_LOCK = Lock()
_LAST_INIT_ATTEMPT = 0.0

def initialize_auraflux_engine():
    """Initializes the singleton engine using all available ModelProviders."""
    global _LAST_INIT_ATTEMPT
    with _INIT_LOCK:
        if time.time() - _LAST_INIT_ATTEMPT < 5.0:
            raise EngineInitializationError("Engine initialization attempted too frequently. Please wait before retrying.")

        _LAST_INIT_ATTEMPT = time.time()

        from agents.models import ModelProvider
        providers = list(ModelProvider.objects.all())
        AurafluxEngineSingleton().initialize(providers=providers)

        return AurafluxEngineSingleton().engine

def get_auraflux_engine():
    try:
        return AurafluxEngineSingleton().engine
    except EngineInitializationError:
        return initialize_auraflux_engine()

def get_client_manager() -> Any:
    """Retrieves the initialized ClientManager instance from the engine."""
    engine = get_auraflux_engine()
    return engine.client_manager if engine and hasattr(engine, 'client_manager') else None

def compose_prompt(
    agent_input_data: Dict[str, Any],
    prompt_template: str,
    template_variables: Dict[str, Any]
) -> Optional[str]:
    """
    Composes the final LLM prompt string by filling the prompt template with rendered data.
    """

    required_variables = set(template_variables.keys())
    missing_variables = required_variables - set(agent_input_data.keys())

    if missing_variables:
        logger.error(
            f"Prompt rendering aborted. Missing required data for variables: {missing_variables}"
        )
        return None

    try:
        composed_prompt = prompt_template
        for key, value in agent_input_data.items():
            str_value = str(value) if value is not None else ""
            composed_prompt = composed_prompt.replace("{{" + key + "}}", str_value)

        return composed_prompt.strip()

    except Exception as e:
        logger.critical(f"Error during prompt template rendering: {e}")
        return None

def get_agent_response(
    agent_name: str,
    agent_role: str,
    system_prompt: str,
    llm_parameters: Dict,
    agent_input_data: Dict[str, Any],
    prompt_template: str,
    template_variables: Dict[str, Any],
    prompt_text=None,
    output_format: Literal['TEXT', 'JSON'] = 'TEXT',
    **kwargs
) -> Any:
    """
    Retrieves the agent response using the AurafluxEngine.
    """
    if prompt_text is None and agent_input_data is None:
        raise ValueError("Either prompt_text or agent_input_data must be provided.")

    if prompt_text is not None:
        prompt = prompt_text
    elif agent_input_data is not None:
        prompt = compose_prompt(agent_input_data, prompt_template, template_variables)
    else:
        raise ValueError("Unable to compose prompt: insufficient data provided.")

    try:
        engine = get_auraflux_engine()

        # Preparing config and payload as per contract (task-01-contract-spec.md)
        agent_config = AgentConfig(
            name=agent_name,
            provider=llm_parameters.get('provider', 'openai'),
            model=llm_parameters.get('model', 'gpt-4'),
            output_format=output_format,
            **llm_parameters
        )

        payload = {
            "messages": [Message(role="user", content=prompt, name='User')],
        }

        # execute_agent signature: (agent_type: str, payload: Dict[str, Any], config: AgentConfig)
        response = async_to_sync(engine.execute_agent)(
            agent_type=agent_role,
            payload=payload,
            config=agent_config
        )

        return response.get('result')
    except Exception as e:
        logger.error(f"Engine execution failed for agent role {agent_role}: {e}")
        raise e

def get_embedding_response(
    embedding_name: str,
    embedding_role: str,
    parameters: Dict[str, Any] | None = None,
    input_text: Union[str, List[str]] | None = None,
    use_batch: bool = False,
    **kwargs
) -> Union[List[float], List[List[float]]]:
    """
    Generates embedding vectors using AurafluxEngine.
    """
    if not input_text:
        raise ValueError("input_text must be provided and cannot be empty.")

    try:
        engine = get_auraflux_engine()
        embedding_config = EmbeddingConfig(
            name=embedding_name,
            provider=kwargs.get('provider', 'default'),
            model=kwargs.get('model', 'default'),
            parameters=parameters or {},
            **kwargs
        )

        payload = {
            "input_text": input_text,
            "use_batch": use_batch or isinstance(input_text, list)
        }

        response = async_to_sync(engine.execute_embedding)(
            embedding_type=embedding_role,
            payload=payload,
            config=embedding_config
        )

        if response.get('status') == 'success':
            result = response.get('result')
            if result is None:
                raise ValueError("Engine returned success but result is None.")
            return result
        else:
            raise RuntimeError(f"Engine execution failed: {response.get('error')}")

    except Exception as e:
        logger.error(
            "Failed to generate embedding for instance '%s' with role '%s': %s",
            embedding_name, embedding_role, str(e)
        )
        raise e

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

    # Use ClientManager for testing/measurements as it works independently
    client_manager = ClientManager(ClientConfig(models=[]))

    provider_id = provider_id or str(uuid4())
    provider_config = ProviderConfig(id=provider_id, name='test', provider_type=provider_type, api_key=api_key)

    async_to_sync(client_manager.initialize)()
    client_manager.instantiate_handler_by_config(provider_config)
    return client_manager.get_available_models(provider_id=provider_id)
