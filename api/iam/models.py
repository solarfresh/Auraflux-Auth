import base64
import os
import secrets

from core.models import BaseModel
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class TargetService(BaseModel):
    """
    Registry for authorized downstream business systems.
    """
    name = models.CharField(max_length=50, unique=True)
    client_id = models.CharField(max_length=50, unique=True)
    _encrypted_client_secret = models.TextField(db_column='client_secret', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def _get_fernet(self):
        key = os.getenv('ENCRYPTION_KEY_64', settings.SECRET_KEY[:32].encode('utf-8').ljust(32, b'='))
        if isinstance(key, str):
            key = key.encode()
        return Fernet(base64.urlsafe_b64encode(key[:32]))

    def set_client_secret(self, raw_secret: str):
        if not raw_secret:
            self._encrypted_client_secret = None
        else:
            fernet = self._get_fernet()
            self._encrypted_client_secret = fernet.encrypt(raw_secret.encode()).decode()

    def get_client_secret(self) -> str:
        if not self._encrypted_client_secret:
            return ""
        try:
            fernet = self._get_fernet()
            return fernet.decrypt(self._encrypted_client_secret.encode()).decode()
        except Exception:
            return "DECRYPTION_ERROR"

    @property
    def client_secret_fingerprint(self):
        raw = self.get_client_secret()
        if raw and raw != "DECRYPTION_ERROR":
            return f"••••{raw[-4:]}"
        return None

    @staticmethod
    def generate_secret() -> str:
        return f"sec_{secrets.token_urlsafe(32)}"


class UserServicePermission(BaseModel):
    """
    Mapping table for user permissions across different business systems.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(TargetService, on_delete=models.CASCADE)
    scopes = models.JSONField(default=list)

    class Meta:
        unique_together = ('user', 'service')