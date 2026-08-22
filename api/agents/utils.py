import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from asgiref.sync import async_to_sync
from auraflux_core.agents import AGENT_REGISTRY, Agent
from auraflux_core.core.clients.client_manager import ClientManager
from auraflux_core.core.schemas.clients import ClientConfig, ProviderConfig
from auraflux_core.core.schemas.messages import Message

logger = logging.getLogger(__name__)

_GLOBAL_CLIENT_MANAGER: Optional[Any] = None

def get_global_client_manager() -> Any:
    """Retrieves the initialized ClientManager instance."""
    if _GLOBAL_CLIENT_MANAGER is None:
        logger.warning("ClientManager has not been initialized. Check agents/apps.py ready() method.")

    return _GLOBAL_CLIENT_MANAGER

def set_global_client_manager(client_manager: Any):
    """Sets the initialized ClientManager instance."""
    global _GLOBAL_CLIENT_MANAGER
    _GLOBAL_CLIENT_MANAGER = client_manager

def compose_prompt(
    agent_input_data: Dict[str, Any],
    prompt_template: str,
    template_variables: Dict[str, Any]
) -> Optional[str]:
    """
    Composes the final LLM prompt string by filling the prompt template with rendered data.

    Args:

    Returns:
        The fully composed prompt string, or None if the template is missing.
    """

    required_variables = set(template_variables.keys())
    missing_variables = required_variables - set(agent_input_data.keys())

    if missing_variables:
        logger.error(
            f"Prompt rendering aborted. Missing required data for variables: {missing_variables}"
        )
        # For production robustness, we might substitute missing variables with a fallback (e.g., 'N/A')
        # or raise a specific error. Here, we return None.
        return None

    try:
        # We need to wrap variable names with curly braces to match the {{var}} syntax
        # often used in templates and then replace them using the dictionary keys.

        # A simple replacement loop is robust against special characters, unlike using .format directly
        # on the entire text which requires careful handling of all existing braces {}.

        composed_prompt = prompt_template
        for key, value in agent_input_data.items():
            # Ensure the value is converted to string for safe insertion
            str_value = str(value) if value is not None else ""

            # Replace the {{key}} placeholder with the actual value
            composed_prompt = composed_prompt.replace("{{" + key + "}}", str_value)

        return composed_prompt.strip()

    except Exception as e:
        logger.critical(f"Error during prompt template rendering: {e}")
        return None

def get_agent_instance(
    agent_name: str,
    agent_role: str,
    system_prompt: str,
    llm_parameters: Dict
) -> Agent:
    """
    Retrieves an instance of the specified agent role, along with its configuration.

    Args:
        agent_name: The name of the agent instance.
        agent_role: The role of the agent (e.g., 'assistant', 'researcher', etc.).
        system_prompt: The system prompt to initialize the agent with.
        llm_parameters: Parameters for configuring the LLM.
    """

    try:
        client_manager = get_global_client_manager()
        if client_manager is None:
            raise RuntimeError("ClientManager is not initialized in AgentsConfig.")

        agent_config = {
            "name": agent_name,
            "system_message": system_prompt,
            **llm_parameters
        }

        agent_registry = AGENT_REGISTRY[agent_role] if agent_role in AGENT_REGISTRY else AGENT_REGISTRY['default']
        agent = agent_registry.agent_class(
            config=agent_registry.config_class(**agent_config),
            client_manager=client_manager
        )

        return agent
    except Exception as e:
        logger.critical("Failed to create agent instance for role %s: %s", agent_role, str(e))
        raise e

def get_agent_response(
    agent_name: str,
    agent_role: str,
    system_prompt: str,
    llm_parameters: Dict,
    agent_input_data: Dict[str, Any],
    prompt_template: str,
    template_variables: Dict[str, Any],
    prompt_text=None,
    tool_args_map: dict | None = None,
    output_format: str = 'text',
    **kwargs
) -> Any:
    """
    Retrieves the agent response based on either a direct prompt text or rendered data.

    Args:
        agent_name: The name of the agent instance.
        agent_role: The role of the agent (e.g., 'assistant', 'researcher
        system_prompt: The system prompt to initialize the agent with.
        llm_parameters: Parameters for configuring the LLM.
        agent_input_data: Data to be used for composing the prompt.
        prompt_template: Template string for the prompt, with placeholders for variables.
        template_variables: Mapping of variable names to their corresponding values for prompt rendering.
        prompt_text: Direct prompt text to send to the agent.
        tool_args_map: Optional mapping of tool names to their arguments for dynamic tool configuration.
        output_format: Desired output format ('text' or 'json').
    """

    if prompt_text is None and agent_input_data is None:
        raise ValueError("Either prompt_text or agent_input_data must be provided.")

    agent = get_agent_instance(agent_name, agent_role, system_prompt, llm_parameters)

    if prompt_text is not None:
        prompt = prompt_text
    elif agent_input_data is not None:
        prompt = compose_prompt(agent_input_data, prompt_template, template_variables)
    else:
        raise ValueError("Unable to compose prompt: insufficient data provided.")

    try:
        message = async_to_sync(agent.generate)(
            messages=[Message(role="user", content=prompt, name='User')],
            tool_args_map=tool_args_map
        )

        if output_format == 'json':
            return json.loads(message.content.replace('```json', '').replace('```', '').strip())
        elif output_format == 'text':
            return message.content
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

    except Exception as e:
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

    client_manager = get_global_client_manager()
    if not provider_id or client_manager is None:
        provider_id = str(uuid4())
        provider_config = ProviderConfig(id=provider_id, name='test', provider_type=provider_type, api_key=api_key)
        client_config = ClientConfig(models=[provider_config])
        client_manager = ClientManager(client_config)
        async_to_sync(client_manager.initialize)()
    else:
        model_provider = model_class.objects.get(id=provider_id)
        provider_config = ProviderConfig(
            id=provider_id,
            provider_type=provider_type.upper(),
            api_key=model_provider.get_api_key()
        )
        client_config = ClientConfig(models=[provider_config])
        client_manager = ClientManager(client_config)
        async_to_sync(client_manager.initialize)()
        set_global_client_manager(client_manager)

    client_manager.instantiate_handler_by_config(provider_config)
    return client_manager.get_available_models(provider_id=provider_id)
