import pytest
from api.services.engine import AurafluxCoreService
from api.agents.models import ModelProvider

@pytest.mark.django_db
def test_engine_initialization_success():
    # Setup
    provider = ModelProvider.objects.create(name="OpenAI", _encrypted_api_key="secret")
    providers_data = [{'id': provider.id, 'name': provider.name, '_encrypted_api_key': provider._encrypted_api_key}]

    # Execute
    engine = AurafluxCoreService()
    result = engine.initialize(providers_data)

    # Assert
    assert result['initialized'] is True
    assert result['loaded_providers_count'] == 1
    assert result['providers_status'][0]['status'] == 'ACTIVE'

@pytest.mark.django_db
def test_engine_initialization_decryption_error():
    # Setup
    providers_data = [{'id': 999, 'name': 'Invalid', '_encrypted_api_key': 'corrupted'}]

    # Execute
    engine = AurafluxCoreService()
    result = engine.initialize(providers_data)

    # Assert
    assert result['initialized'] is True
    assert result['loaded_providers_count'] == 1
