import os
from pathlib import Path

from adrf.views import APIView
from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema, inline_serializer
from iam.models import TargetService, UserServicePermission
from jose import jwk
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken
from users.permissions import IsAdmin


class ClientCredentialsTokenView(APIView):
    """
    Issues short-lived JWT access tokens using Client Credentials authentication.
    """
    permission_classes = []

    async def post(self, request):
        client_id = request.data.get('client_id')
        client_secret = request.data.get('client_secret')

        if not client_id or not client_secret:
            return Response(
                {'error': 'Both "client_id" and "client_secret" are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Query target system
        try:
            service = await TargetService.objects.aget(client_id=client_id, is_active=True)
        except TargetService.DoesNotExist:
            return Response(
                {'error': 'Invalid client credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 2. Decrypt and verify client_secret
        stored_secret = await sync_to_async(service.get_client_secret)()
        if stored_secret == "DECRYPTION_ERROR" or stored_secret != client_secret:
            return Response(
                {'error': 'Invalid client credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 3. Issue short-lived Access Token
        token = AccessToken()
        token['aud'] = service.client_id
        token['scope'] = [f"{service.client_id}:access"]

        return Response({
            'access_token': str(token),
            'expires_in': 900,
            'token_type': 'Bearer'
        })


class JWKSView(APIView):
    """
    Public endpoint exposing the JSON Web Key Set (JWKS).
    Used by downstream services (e.g., biz-system-b) to fetch public keys for JWT verification.
    """
    _cached_jwk = None
    authentication_classes = []
    permission_classes = []

    @classmethod
    def _get_jwk(cls):
        if cls._cached_jwk is None:
            verifying_key_path = os.getenv('VERIFYING_KEY_PATH', '')

            if not verifying_key_path or not os.path.exists(verifying_key_path):
                return None

            pem_key = Path(verifying_key_path).read_text()
            jwk_key = jwk.construct(pem_key, algorithm='RS256').to_dict()
            jwk_key['use'] = 'sig'
            jwk_key['alg'] = 'RS256'
            jwk_key['kid'] = 'auth-system-master-key'

            cls._cached_jwk = jwk_key

        return cls._cached_jwk

    async def get(self, request):
        jwk_key = self._get_jwk()

        if not jwk_key:
            return Response(
                {'error': 'Public key file not found.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'keys': [jwk_key]
        })


class TokenExchangeView(APIView):
    permission_classes = [IsAuthenticated]

    async def post(self, request):
        user = request.user
        target_service_id = request.data.get('target_service')
        if not target_service_id:
            return Response({'error': 'target_service is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_perm = await UserServicePermission.objects.select_related(
                'service'
            ).aget(
                user=user, service__client_id=target_service_id, service__is_active=True
            )
            service = user_perm.service
        except UserServicePermission.DoesNotExist:
            return Response({'error': 'Permission denied for this service'}, status=status.HTTP_403_FORBIDDEN)

        token = AccessToken.for_user(user)
        token['user_id'] = user.id
        token['aud'] = service.client_id
        token['scope'] = user_perm.scopes

        return Response({
            'access_token': str(token),
            'expires_in': 900
        })


@extend_schema(
    summary="Register a downstream service and issue client credentials",
    description="This endpoint allows admin users to register a downstream service and receive client credentials (client_id and client_secret). The client_secret is only returned once and should be stored securely.",
    request=inline_serializer(
        name='ServiceRegisterRequest',
        fields={
            'name': serializers.CharField(help_text="Name of the downstream service"),
            'client_id': serializers.CharField(help_text="Unique client identifier for the service"),
        }
    ),
    responses={
        201: inline_serializer(
            name='ServiceRegisterResponse',
            fields={
                'message': serializers.CharField(help_text="Success message"),
                'credentials': serializers.DictField(child=serializers.CharField(), help_text="Client credentials (client_id and client_secret)")
            }
        ),
        400: inline_serializer(
            name='ServiceRegisterErrorResponse',
            fields={
                'error': serializers.CharField(help_text="Error message")
            }
        ),
        409: inline_serializer(
            name='ServiceRegisterConflictResponse',
            fields={
                'error': serializers.CharField(help_text="Conflict error message")
            }
        )
    }
)
class ServiceRegisterView(APIView):
    """
    Endpoint for registering downstream services and issuing client credentials.
    Restricted to admin users / CI/CD pipeline service accounts.
    """
    permission_classes = [IsAdmin]

    async def post(self, request):
        name = request.data.get('name')
        client_id = request.data.get('client_id')

        if not name or not client_id:
            return Response(
                {'error': 'Both "name" and "client_id" are required fields.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if await TargetService.objects.filter(client_id=client_id).aexists():
            return Response(
                {'error': f'Service with system_id "{client_id}" is already registered.'},
                status=status.HTTP_409_CONFLICT
            )

        # 1. Generate raw secret
        raw_secret = TargetService.generate_secret()

        # 2. Create target system record and encrypt client_secret
        service = TargetService(
            name=name,
            client_id=client_id,
            is_active=True
        )
        await sync_to_async(service.set_client_secret)(raw_secret)
        await service.asave()

        # 3. Return credentials (ONCE ONLY)
        return Response(
            {
                'message': 'Service registered successfully. Store the client_secret securely.',
                'credentials': {
                    'client_id': service.client_id,
                    'client_secret': raw_secret,
                }
            },
            status=status.HTTP_201_CREATED
        )
