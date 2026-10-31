import pytest
from unittest.mock import Mock, patch, AsyncMock
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

@pytest.mark.django_db
def test_get_embedding_response_success_single():
    # Setup
    mock_engine = Mock()
    mock_engine.execute_embedding = AsyncMock(return_value={
        "status": "success",
        "result": [0.1, 0.2, 0.3]
    })
    with patch("agents.utils.get_auraflux_engine", return_value=mock_engine):
        # Call
        result = get_embedding_response(
            embedding_name="test_embedding",
            embedding_role="default",
            parameters={"model": "test"},
            input_text="Hello Auraflux"
        )

        # Assert
        assert result == [0.1, 0.2, 0.3]
        mock_engine.execute_embedding.assert_called_once()
        assert mock_engine.execute_embedding.call_args[1]["payload"]["input_text"] == "Hello Auraflux"

@pytest.mark.django_db
def test_get_embedding_response_success_batch():
    # Setup
    mock_engine = Mock()
    mock_engine.execute_embedding = AsyncMock(return_value={
        "status": "success",
        "result": [[0.1, 0.2], [0.3, 0.4]]
    })
    with patch("agents.utils.get_auraflux_engine", return_value=mock_engine):
        # Call
        result = get_embedding_response(
            embedding_name="test_embedding",
            embedding_role="default",
            parameters={"model": "test"},
            input_text=["Doc 1", "Doc 2"],
            use_batch=True
        )

        # Assert
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_engine.execute_embedding.assert_called_once()
        assert mock_engine.execute_embedding.call_args[1]["payload"]["input_text"] == ["Doc 1", "Doc 2"]

@pytest.mark.django_db
def test_get_embedding_response_empty_input():
    # Test empty string
    with pytest.raises(ValueError, match="input_text must be provided and cannot be empty"):
        get_embedding_response("test", "default", {}, "")

    # Test empty list
    with pytest.raises(ValueError, match="input_text must be provided and cannot be empty"):
        get_embedding_response("test", "default", {}, [])

    # Test None
    with pytest.raises(ValueError, match="input_text must be provided and cannot be empty"):
        get_embedding_response("test", "default", {}, None)

@pytest.mark.django_db
def test_get_embedding_response_engine_failure():
    # Setup
    mock_engine = Mock()
    mock_engine.execute_embedding = AsyncMock(return_value={
        "status": "failed",
        "error": "Execution failed"
    })
    with patch("agents.utils.get_auraflux_engine", return_value=mock_engine):
        # Call & Assert
        with pytest.raises(RuntimeError, match="Execution failed"):
            get_embedding_response(
                embedding_name="test_embedding",
                embedding_role="default",
                parameters={"model": "test"},
                input_text="test input"
            )
