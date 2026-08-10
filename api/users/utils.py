from asgiref.sync import sync_to_async
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer


@sync_to_async
def get_refreshed_tokens_sync(refresh_token):
    """
    Synchronous wrapper function to perform the blocking token refresh logic.
    This function will be run in a separate thread.
    """
    serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
    serializer.is_valid(raise_exception=True)

    # Extract access and optional new refresh token
    validated = getattr(serializer, 'validated_data', None) or {}
    new_access_token = validated.get('access')

    # Optionally, retrieve a new refresh token if rotation is enabled
    new_refresh_token = validated.get('refresh')

    if not new_access_token:
        raise AuthenticationFailed('Failed to refresh access token.')

    return new_access_token, new_refresh_token
