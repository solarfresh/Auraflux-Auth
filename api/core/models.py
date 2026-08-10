import uuid

from django.db import models


class BaseModel(models.Model):
    """
    An abstract base class that provides self-updating 'created_at'
    and 'updated_at' fields, using UUIDs for primary keys to ensure
    system-wide unique identification.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this entity."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The timestamp when this record was first created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="The timestamp when this record was last modified."
    )

    class Meta:
        abstract = True
