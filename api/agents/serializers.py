import logging

from adrf.serializers import ModelSerializer
from agents.models import ModelFamilies, ModelProvider
from rest_framework import serializers

logger = logging.getLogger(__name__)


class ModelFamiliesSerializer(ModelSerializer):
    displayName = serializers.CharField(source='display_name')

    class Meta:
        model = ModelFamilies
        fields = '__all__'


class ModelProviderSerializer(ModelSerializer):
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    type = serializers.CharField(source='provider_type')
    clientId = serializers.CharField(source='client_id')
    baseUrl = serializers.URLField(source='base_url', required=False, allow_blank=True)
    latencyMs = serializers.IntegerField(source='latency_ms', default=999)
    lastVerifiedAt = serializers.DateTimeField(source='last_verified_at')
    apiKeyFingerprint = serializers.ReadOnlyField(source='api_key_fingerprint')
    apiKey = serializers.CharField(
        source='api_key',
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="The raw API key to be encrypted and stored."
    )
    supportedFamilies = ModelFamiliesSerializer(source='supported_families', many=True, read_only=True)

    class Meta:
        model = ModelProvider
        fields = [
            'id', 'name', 'type', 'clientId', 'apiKey', 'apiKeyFingerprint',
            'baseUrl', 'status', 'user', 'latencyMs', 'lastVerifiedAt',
            'supportedFamilies', 'createdAt', 'updatedAt'
        ]
        extra_kwargs = {
            'id': {'read_only': True},
            'user': {'write_only': True},
        }

    def create(self, validated_data):
        api_key = validated_data.pop('api_key', None)
        instance = ModelProvider.objects.create(**validated_data)

        if api_key:
            instance.set_api_key(api_key)
            instance.save()

        return instance

    def update(self, instance, validated_data):
        api_key = validated_data.pop('api_key', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if api_key:
            instance.set_api_key(api_key)

        instance.save()
        return instance