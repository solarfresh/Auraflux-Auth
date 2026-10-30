import pytest
from agents.utils import get_agent_response, get_embedding_response
from services.exceptions import EngineInitializationError

@pytest.mark.django_db
def test_get_agent_response_without_initialization():
    # Verify EngineInitializationError is raised when engine is not initialized
    from services.engine import AurafluxEngineSingleton
    AurafluxEngineSingleton()._initialized = False # Force uninitialized state

    with pytest.raises(EngineInitializationError):
        get_agent_response(
            agent_name="test_agent",
            agent_role="default",
            system_prompt="You are a helpful assistant.",
            llm_parameters={
                "model": "gpt-4o",
                "provider": "openai",
                "temperature": 0.7,
                "max_tokens": 100
            },
            agent_input_data={"data": "test"},
            prompt_template="Test: {{data}}",
            template_variables={"data": "test"}
        )

@pytest.mark.django_db
def test_get_embedding_response_without_initialization():
    # Verify EngineInitializationError is raised when engine is not initialized
    from services.engine import AurafluxEngineSingleton
    AurafluxEngineSingleton()._initialized = False # Force uninitialized state

    with pytest.raises(EngineInitializationError):
        get_embedding_response(
            embedding_name="test_embedding",
            embedding_role="default",
            parameters={
                "model": "text-embedding-3-small",
                "provider": "openai",
                "dimensions": 1536
            },
            input_text="Test input"
        )
