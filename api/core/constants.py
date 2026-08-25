from django.db import models
from django.utils.translation import gettext_lazy as _


class OperationalStatus(models.TextChoices):
    ONLINE = 'ONLINE', _('Online')
    OFFLINE = 'OFFLINE', _('Offline')
    CONNECTING = 'CONNECTING', _('Connecting')
    MAINTENANCE = 'MAINTENANCE', _('Maintenance')
    DEGRADED = 'DEGRADED', _('Degraded')
