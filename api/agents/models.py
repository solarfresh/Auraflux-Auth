import os

from agents.constants import ProviderType
from core.constants import OperationalStatus
from core.models import BaseModel
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class ModelFamilies(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    input_token_limit = models.PositiveIntegerField()
    output_token_limit = models.PositiveIntegerField()


class ModelProvider(BaseModel):
    # --- Engine Identity ---
    name = models.CharField(max_length=100)
    provider_type = models.CharField(
        max_length=20,
        choices=ProviderType.choices,
        default=ProviderType.GOOGLE
    )

    # --- Infrastructure & Security ---
    _encrypted_api_key = models.TextField(db_column='api_key', blank=True, null=True)
    base_url = models.URLField(blank=True, null=True)

    # --- Diagnostics (Rule 14: Pulse) ---
    status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.OFFLINE
    )
    latency_ms = models.PositiveIntegerField(blank=True, null=True)
    last_verified_at = models.DateTimeField(blank=True, null=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="The ID of the user owning this provider."
    )
    supported_families = models.ManyToManyField(
        ModelFamilies,
        blank=True
    )

    client = models.ForeignKey(
        'iam.TargetService',
        related_name='model_providers',
        to_field='client_id',
        on_delete=models.CASCADE,
        db_column='client_id'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.provider_type})"

    # --- Security Logic (Cognitive Sovereignty) ---

    def _get_fernet(self):
        key = os.getenv('ENCRYPTION_KEY_64', settings.SECRET_KEY[:32].encode('utf-8').ljust(32, b'='))
        import base64
        if isinstance(key, str):
            key = key.encode()
        return Fernet(base64.urlsafe_b64encode(key[:32]))

    def set_api_key(self, raw_key: str):
        if not raw_key:
            self._encrypted_api_key = None
        else:
            fernet = self._get_fernet()
            self._encrypted_api_key = fernet.encrypt(raw_key.encode()).decode()

    def get_api_key(self) -> str:
        if not self._encrypted_api_key:
            return ""
        try:
            fernet = self._get_fernet()
            return fernet.decrypt(self._encrypted_api_key.encode()).decode()
        except Exception:
            return "DECRYPTION_ERROR"

    @property
    def api_key_fingerprint(self):
        raw = self.get_api_key()
        if raw and raw != "DECRYPTION_ERROR":
            return f"••••{raw[-4:]}"
        return None
