from django.apps import AppConfig


class MessagingConfig(AppConfig):
    """
    The responsibility is responsibility is Project Management and State Persistence.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messaging'
    label = 'messaging'
