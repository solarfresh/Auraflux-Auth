from django.db import models
from django.utils.translation import gettext_lazy as _


class ProviderType(models.TextChoices):
    GOOGLE = 'GOOGLE', _('Google')
    OPENAI = 'OPENAI', _('OpenAI')
    ANTHROPIC = 'ANTHROPIC', _('Anthropic')
    LOCAL = 'LOCAL', _('Custom')
