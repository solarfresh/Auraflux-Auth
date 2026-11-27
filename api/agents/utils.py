import logging
import os
import time
from threading import Lock
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import uuid4

from asgiref.sync import async_to_sync
from auraflux_core.agents import AGENT_REGISTRY
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

def _reset_after_fork_in_child(**kwargs):
    global _LAST_INIT_ATTEMPT, _INIT_LOCK
    _LAST_INIT_ATTEMPT = 0.0
    _INIT_LOCK = Lock()

os.register_at_fork(after_in_child=_reset_after_fork_in_child)

def initialize_auraflux_engine():
    """Initializes the singleton engine using all available ModelProviders."""
    global _LAST_INIT_ATTEMPT, _INIT_LOCK
    current_pid = os.getpid()

    with _INIT_LOCK:
        singleton = AurafluxEngineSingleton()
        now = time.time()

        if singleton.initialized and singleton.pid == current_pid:
            return singleton.engine

        if now - _LAST_INIT_ATTEMPT < 5.0:
            raise EngineInitializationError("Engine initialization attempted too frequently. Please wait before retrying.")

        _LAST_INIT_ATTEMPT = now

        from agents.models import ModelProvider
        providers = list(ModelProvider.objects.all())
        async_to_sync(singleton.initialize)(providers=providers)

        return singleton.engine

def get_auraflux_engine():
    try:
        singleton = AurafluxEngineSingleton()
        return singleton.engine
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
    type: str,
    config: Dict[str, Any],
    payload: Dict[str, Any],
    **kwargs
) -> Any:
    """
    Retrieves the agent response using the AurafluxEngine with standardized unified contract.
    Decoupled via name, type, config, payload unpacking provider, model, and system_prompt.
    """
    agent_type = type if type else 'default'

    try:
        engine = get_auraflux_engine()

        AgentConfigClass = AGENT_REGISTRY[agent_type].config_class
        agent_config = AgentConfigClass(**config)
        response = async_to_sync(engine.execute_agent)(
            agent_type=agent_type,
            payload=payload,
            config=agent_config
        )

        return response.get('result')
    except Exception as e:
        logger.error(f"Engine execution failed for agent type {type}: {e}")
        raise e

def get_embedding_response(
    name: str,
    type: str,
    config: Dict[str, Any],
    payload: Dict[str, Any],
    **kwargs
) -> Union[List[float], List[List[float]]]:
    """
    Generates embedding vectors using AurafluxEngine with standardized unified contract.
    Decoupled via name, type, config, payload unpacking provider and model.
    """

    try:
        engine = get_auraflux_engine()
        embedding_config = EmbeddingConfig(**config)
        response = async_to_sync(engine.execute_embedding)(
            embedding_type=type,
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
            "Failed to generate embedding for instance '%s' with type '%s': %s",
            name, type, str(e)
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
