import logging

from adrf.views import APIView
from agents.models import ModelProvider
from agents.serializers import ModelProviderSerializer
from agents.utils import measure_model_provider_connection
from asgiref.sync import sync_to_async
from core.utils import (create_serialized_data, get_serialized_data,
                        get_serialized_data_by_id,
                        update_serialized_data_by_id)
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from messaging.constants import UpdateModelFamilies
from messaging.tasks import publish_event
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class ModelProviderView(APIView):

    permission_classes = [IsAuthenticated]

    async def get(self, request):
        user = request.user

        data = await sync_to_async(get_serialized_data)({'user_id': user.id}, ModelProvider, ModelProviderSerializer, many=True)
        return Response(data, status=status.HTTP_200_OK)

    async def post(self, request):
        user = request.user
        request_data = request.data
        request_data['user'] = str(user.id)
        try:
            data = await sync_to_async(create_serialized_data)(request_data, ModelProviderSerializer)
            publish_event.delay(
                event_type=UpdateModelFamilies.name,
                payload={
                    'provider_id': data['id'],
                },
                queue=UpdateModelFamilies.queue
            )

            return Response(data, status=status.HTTP_200_OK)
        except Exception as errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)


class ModelProviderAvailableView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Obtain Available Models for a Provider",
        description=(
            "Checks the connection to a specified model provider using the provided API key and returns a list of available models. "
            "This endpoint is used to validate the provider configuration and to retrieve the models that can be used for agent configurations."
        ),
        request=OpenApiTypes.OBJECT,
        examples=[
            OpenApiExample(
                'Valid OpenAI Provider',
                value={"providerType": "openai", "apiKey": "sk-xxxx..."},
                response_only=True,
            )
        ]
    )
    async def post(self, request):
        request_data = request.data
        api_key = request_data.get('apiKey')
        provider_type = request_data.get('providerType')
        provider_id = request_data.get('providerId', '')
        available_models = await sync_to_async(measure_model_provider_connection)(provider_type, api_key, provider_id, ModelProvider)
        return Response(available_models, status=status.HTTP_200_OK)


class ModelProviderDetailView(APIView):

    permission_classes = [IsAuthenticated]

    async def get(self, request, provider_id):
        data = await sync_to_async(get_serialized_data_by_id)(provider_id, ModelProvider, ModelProviderSerializer)
        return Response(data, status=status.HTTP_200_OK)

    async def put(self, request, provider_id):
        request_data = request.data
        try:
            data = await sync_to_async(update_serialized_data_by_id)(provider_id, request_data, ModelProvider, ModelProviderSerializer)
            publish_event.delay(
                event_type=UpdateModelFamilies.name,
                payload={
                    'provider_id': data['id'],
                },
                queue=UpdateModelFamilies.queue
            )

            return Response(data, status=status.HTTP_200_OK)
        except Exception as errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
