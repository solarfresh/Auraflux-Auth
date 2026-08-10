from typing import Any, Dict
from uuid import UUID

from django.conf import settings
from rest_framework.exceptions import ValidationError


def create_serialized_data(data: Dict[str, Any], serializer_class, **save_kwargs):
    serializer = serializer_class(data=data)
    if serializer.is_valid():
        serializer.save(**save_kwargs)
        return serializer.data
    else:
        raise ValidationError(serializer.errors)

def delete_instance_by_query(query: Dict, model_class):
    instance = model_class.objects.get(**query)
    instance.delete()

def get_serialized_data(query: Dict, model_class, serializer_class, many=True):
    if (many):
        instances = model_class.objects.filter(**query).all()
    else:
        instances = model_class.objects.filter(**query).get()

    serializer = serializer_class(instances, many=many)
    return serializer.data

def get_serialized_data_by_id(id: UUID, model_class, serializer_class):
    instance = model_class.objects.get(id=id)
    serializer = serializer_class(instance)
    return serializer.data

def get_user_search_cache_key(user_id):
    """Generates a unique cache key for a user's search results."""
    return f"{settings.SEARCH_CACHE_KEY_PREFIX}:{user_id}"

def update_serialized_data_by_id(id: UUID, data: Dict[str, Any], model_class, serializer_class):
    instance = model_class.objects.get(id=id)
    serializer = serializer_class(
        instance=instance,
        data=data,
        partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return serializer.data
    else:
        raise ValidationError(serializer.errors)

def update_serialized_data_by_query(query: Dict, data: Dict[str, Any], model_class, serializer_class):
    instance = model_class.objects.get(**query)
    serializer = serializer_class(
        instance=instance,
        data=data,
        partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return serializer.data
    else:
        raise ValidationError(serializer.errors)
