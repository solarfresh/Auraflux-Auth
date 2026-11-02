import pytest
import os
from unittest.mock import patch, MagicMock
from django.conf import settings

def pytest_configure(config):
    # Dynamically set log path and override Logging to avoid file path errors
    os.environ['LOG_FILE_PATH'] = '/dev/null'
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

    from django.conf import settings
    # Override logging to use a safe handler
    settings.LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {'class': 'logging.StreamHandler'},
        },
        'root': {'handlers': ['console'], 'level': 'INFO'},
    }
    if not settings.configured:
        settings.configure()

@pytest.fixture(autouse=True)
def mock_infrastructure():
    # Mocking open for SIGNING_KEY, VERIFYING_KEY
    with patch("builtins.open", side_effect=lambda file, *args, **kwargs: MagicMock(read=lambda: "dummy-key-content") if not str(file).endswith('/dev/null') else open(file, *args, **kwargs)), \
         patch("messaging.tasks.publish_event.delay") as mock_publish:
        yield {
            "publish_event": mock_publish,
        }

@pytest.fixture
def test_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="test_weaver",
        email="weaver@auraflux.ai",
        password="secure_password_123"
    )

@pytest.fixture
def authenticated_api_client(test_user):
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=test_user)
    return client
