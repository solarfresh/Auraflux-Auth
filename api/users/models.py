import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    A custom user model that inherits from Django's AbstractUser.

    This model can be extended with custom fields and methods as needed,
    while still using Django's powerful built-in authentication system.
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        USER = 'user', 'User'

    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4,
        help_text="Unique identifier for the user."
    )

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
        verbose_name="role"
    )

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        db_table = 'users_user'
