import pytest
from unittest.mock import patch, MagicMock

# -------------------------------------------------------------------------
# 1. Global Environment & Third-Party Mocks
# -------------------------------------------------------------------------

def pytest_configure(config):
    """
    Hook into pytest configuration to modify Django settings dynamically before setup.
    This safely bypasses the 'logfile' handler directory dependency during tests.
    """
    from django.conf import settings

    # Check if Django settings are configured and LOGGING dict exists
    if hasattr(settings, "LOGGING") and "handlers" in settings.LOGGING:
        if "logfile" in settings.LOGGING["handlers"]:
            # Dynamically switch the file handler to a safe console output or NullHandler
            settings.LOGGING["handlers"]["logfile"] = {
                "class": "logging.StreamHandler",  # Redirect to stdout/stderr
                "formatter": "verbose" if "verbose" in settings.LOGGING.get("formatters", {}) else None
            }

@pytest.fixture(autouse=True)
def mock_external_infrastructure():
    """
    Globally mock out underlying asynchronous message brokers or network operations
    to ensure tests run in total isolation without hitting live services.
    """
    # Mock the publish_event Celery task to prevent actual network/broker delivery
    with patch("messaging.tasks.publish_event.delay") as mock_publish, \
         patch("canvases.tasks.publish_event.delay") as mock_canvas_publish:
        yield {
            "publish_event": mock_publish,
            "canvas_publish": mock_canvas_publish
        }


# -------------------------------------------------------------------------
# 2. Reusable Database Fixtures (Data Factories)
# -------------------------------------------------------------------------

@pytest.fixture
def test_user(db):
    """
    Provides a standardized user model instance for authentication-guarded scopes.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model() if hasattr(get_user_model(), 'objects') else None

    # Fallback to dynamic creation if user app relies on standard auth architecture
    if not User:
        from django.contrib.auth.models import User

    return User.objects.create_user(
        username="test_weaver",
        email="weaver@auraflux.ai",
        password="secure_password_123"
    )


@pytest.fixture
def test_project(db, test_user):
    """
    Provides a basic Research Project container mapped to the testing user session.
    """
    from projects.models import ResearchProject
    return ResearchProject.objects.create(
        name="Auraflux Core Synthesis",
        description="Evaluating automated multi-disciplinary graph anchoring.",
        user=test_user
    )


# @pytest.fixture
# def test_canvas(db, test_project):
#     """
#     Provides a concrete base Canvas workspace assigned to the generated target project.
#     """
#     from canvases.models import Canvas
#     return Canvas.objects.create(
#         name="Main Operational Weaver View",
#         project=test_project
#     )


# -------------------------------------------------------------------------
# 3. API Client Fixtures (For Integration Endpoint Testing)
# -------------------------------------------------------------------------

@pytest.fixture
def authenticated_api_client(test_user):
    """
    Provides an adrf / rest_framework API Client injected with pre-verified
    credentials acting as the logged-in target user context.
    """
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=test_user)
    return client