from adrf.views import APIView
from django.conf import settings
from django.contrib.auth import aauthenticate, get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from users.permissions import IsAdmin, IsSelfOrAdmin
from users.serializers import UserSerializer

from .serializers import LoginRequestSerializer, LoginResponseSerializer
from .utils import get_refreshed_tokens_sync

User = get_user_model()


class LoginView(APIView):
    permission_classes = [AllowAny]

    # FIX: Explicitly disable all authentication classes for this view.
    # This overrides the global DEFAULT_AUTHENTICATION_CLASSES setting.
    authentication_classes = []

    @extend_schema(
        summary="User Login and JWT Cookie Generation",
        description="Authenticates the user and sets Access and Refresh JWT tokens in **HttpOnly cookies**.",
        # 1. Request Body Schema
        request=LoginRequestSerializer,
        # 2. Response Schema (Success and Failure)
        responses={
            200: LoginResponseSerializer,
            400: OpenApiTypes.OBJECT, # Simple error object
        },
        # 3. Examples for clarity
        examples=[
            OpenApiExample(
                'Successful Login',
                value={'id': 1, 'username': 'testuser', 'email': 'user@example.com', 'is_admin': False},
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                'Invalid Credentials',
                value={'error': 'Invalid credentials.'},
                response_only=True,
                status_codes=['400']
            ),
        ]
    )
    async def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        input_serializer = LoginRequestSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        user = await aauthenticate(request, username=username, password=password)

        if user is not None:
            # Generate both access and refresh tokens
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token

            serializer = UserSerializer(user)

            response = Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

            # Set cookies with HttpOnly and secure flags
            response.set_cookie(
                key=str(settings.SIMPLE_JWT['AUTH_COOKIE']),
                value=str(access),
                expires=str(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']),
                secure=bool(settings.SIMPLE_JWT['AUTH_COOKIE_SECURE']),
                httponly=bool(settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY']),
                samesite=str(settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'])
            )
            response.set_cookie(
                key=str(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']),
                value=str(refresh),
                expires=str(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']),
                secure=bool(settings.SIMPLE_JWT['AUTH_COOKIE_SECURE']),
                httponly=bool(settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY']),
                samesite=str(settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'])
            )

            return response
        else:
            return Response({
                'error': 'Invalid credentials.'
            }, status=status.HTTP_400_BAD_REQUEST)


# @method_decorator(csrf_exempt, name='dispatch') # Apply csrf_exempt to the view
class RefreshTokenView(APIView):
    # 🎯 The essential fix: allow the request to bypass standard authentication
    permission_classes = [AllowAny]

    # FIX: Explicitly disable all authentication classes for this view.
    # This overrides the global DEFAULT_AUTHENTICATION_CLASSES setting.
    authentication_classes = []

    async def post(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])

        if not refresh_token:
            raise AuthenticationFailed('Refresh token is missing.')

        try:
            new_access_token, new_refresh_token = await get_refreshed_tokens_sync(refresh_token)

            # Prepare the response and set the new access token cookie
            response = Response({'message': 'Access token refreshed.'}, status=status.HTTP_200_OK)
            response.set_cookie(
                key=str(settings.SIMPLE_JWT['AUTH_COOKIE']),
                value=str(new_access_token),
                expires=str(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']),
                secure=bool(settings.SIMPLE_JWT['AUTH_COOKIE_SECURE']),
                httponly=bool(settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY']),
                samesite=str(settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'])
            )

            if new_refresh_token:
                response.set_cookie(
                    key=str(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']),
                    value=str(new_refresh_token),
                    expires=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
                    secure=bool(settings.SIMPLE_JWT['AUTH_COOKIE_SECURE']),
                    httponly=bool(settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY']),
                    samesite=str(settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'])
                )

            return response

        except AuthenticationFailed as e:
            # Re-raise authentication failures unchanged
            raise
        except Exception as e:
            raise AuthenticationFailed('Refresh token is invalid or expired.')


class UserCreateView(CreateModelMixin, GenericAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Handles the POST request to create a new user
        return self.create(request, *args, **kwargs)


class UserStatusView(APIView):
    """
    Returns the details of the currently authenticated user (profile check).
    Requires a valid JWT Access Token in the cookie.
    """
    # 🎯 Requires the user to be authenticated via the JWT Cookie Middleware
    permission_classes = [IsAuthenticated]

    # We do NOT need to set authentication_classes = [] here.
    # It must rely on the global DEFAULT_AUTHENTICATION_CLASSES, which
    # should include your JWTCookieAuthentication class for this to work.

    @extend_schema(
        summary="Get Current Authenticated User Status",
        description="Checks session validity and returns key details of the logged-in user.",
        responses={
            200: UserSerializer,
            401: {"description": "Authentication failed (token missing or invalid)."},
        },
        examples=[
            OpenApiExample(
                'Authenticated User Data',
                value={'id': 1, 'username': 'testuser', 'email': 'user@example.com', 'is_admin': False},
                response_only=True,
                status_codes=['200']
            )
        ]
    )
    async def get(self, request):
        """
        Since permission_classes = [IsAuthenticated] passed, request.user is an
        authenticated User object, fetched by the JWTAuthMiddleware/JWTCookieAuthentication.
        """
        # The serializer will validate and structure the data from the user object
        serializer = UserSerializer(request.user)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        # Use different permissions based on the action
        if self.action == 'list':
            # Only admins can view the list of all users
            permission_classes = [IsAdmin]
        elif self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            # For specific user objects, allow admins or the user themselves
            permission_classes = [IsSelfOrAdmin]
        else:
            # For other actions (like 'create'), allow any authenticated user
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
