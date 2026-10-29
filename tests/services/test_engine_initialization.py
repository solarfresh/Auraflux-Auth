import pytest
from django.contrib.auth import get_user_model
from agents.models import ModelProvider
from services.engine import AurafluxEngineSingleton

User = get_user_model()

@pytest.mark.django_db
def test_singleton_instance():
    # Verify that AurafluxEngineSingleton is a singleton
    engine1 = AurafluxEngineSingleton()
    engine2 = AurafluxEngineSingleton()
    assert engine1 is engine2

@pytest.mark.django_db
def test_happy_path_initialization():
    user = User.objects.create_user(username="testuser")
    # Setup test data
    provider = ModelProvider.objects.create(name="test_provider", provider_type="openai", user=user)
    provider.save()

    engine = AurafluxEngineSingleton()
    # The initialization expects providers as a list of dictionaries
    payload = engine.initialize([{'id': provider.id, 'name': provider.name, 'provider_type': 'openai', 'api_key': 'valid_key'}])

    assert payload['loaded_providers_count'] == 1
    assert payload['providers_status'][0]['status'] == "ACTIVE"

@pytest.mark.django_db
def test_decryption_error_isolation():
    user = User.objects.create_user(username="testuser2")
    # Setup data
    provider = ModelProvider.objects.create(name="bad_provider", provider_type="openai", user=user)
    provider.save()

    engine = AurafluxEngineSingleton()
    # Simulate the DECRYPTION_ERROR case by passing a specific key
    payload = engine.initialize([{'id': provider.id, 'name': provider.name, 'provider_type': 'openai', 'api_key': 'DECRYPTION_ERROR_SIM'}])

    # Spec requires it to be DECRYPTION_ERROR.
    assert payload['providers_status'][0]['status'] == "DECRYPTION_ERROR"

@pytest.mark.django_db
def test_empty_database_initialization():
    # Setup empty database scenario
    engine = AurafluxEngineSingleton()
    payload = engine.initialize([])

    assert payload['loaded_providers_count'] == 0
