from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from channels.db import database_sync_to_async


class JWTCookieAuthentication(JWTAuthentication):
    """
    Looks only for the Access Token in the HTTP-only cookie.
    If the token is expired/invalid, it returns None/None to allow the
    view permission checks to return the 401 or 403, as expected.
    """
    def authenticate(self, request):
        # Look for the token in the designated cookie
        raw_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE'])

        if raw_token:
            try:
                # Attempt to validate the token
                validated_token = self.get_validated_token(raw_token)
                # Success: Return the user and validated token
                return self.get_user(validated_token), validated_token
            except (InvalidToken, TokenError):
                # IMPORTANT: If the token is invalid or expired,
                # we return None to indicate no authentication was provided.
                # This allows DRF to proceed to permission checks and ultimately
                # return a 401 if the view requires IsAuthenticated.
                return None

        # If no cookie token is found, return None
        # Do NOT fall back to super().authenticate(request) as it checks headers
        # which can confuse a cookie-only API.
        return None


class JWTAuthMiddleware:
    """
    Middleware that populates the scope['user'] based on a JWT Access Token in a cookie.
    """
    def __init__(self, inner):
        # Store the next layer (inner application)
        self.inner = inner
        self.jwt_auth = JWTCookieAuthentication()

    async def __call__(self, scope, receive, send):
        # We only care about the 'websocket' protocol
        if scope['type'] == 'websocket':
            # Run the synchronous token validation function asynchronously
            scope['user'] = await self.get_user_from_token(scope)

        # Call the next layer in the stack (the consumer)
        return await self.inner(scope, receive, send)

    @database_sync_to_async
    def get_user_from_token(self, scope):
        """
        Looks for the JWT token in the connection scope's cookies and validates it.
        Returns a Django User object or AnonymousUser.
        """
        # 1. Get cookies from the scope
        # Channels puts the parsed HTTP cookies into scope['cookies']
        headers = dict(scope.get('headers', []))
        raw_cookie_string = headers.get(b'cookie', {})
        cookie = self.parse_cookie_string(raw_cookie_string)

        # 2. Extract the raw token using the same settings key as your DRF class
        auth_cookie_key = settings.SIMPLE_JWT['AUTH_COOKIE']
        raw_token = cookie.get(auth_cookie_key)
        if not raw_token:
            return None

        try:
            # 3. Validate the token and get the user
            validated_token = self.jwt_auth.get_validated_token(raw_token)
            user = self.jwt_auth.get_user(validated_token)

            # NOTE: We return the user object, not the (user, token) tuple
            return user if user else None

        except (InvalidToken, TokenError) as e:
            # 4. Handle invalid/expired tokens by returning AnonymousUser
            return None
        except Exception as e:
            # Catch any other unexpected errors
            return None

    def parse_cookie_string(self, raw_cookie_string):
        cookie_string = raw_cookie_string.decode().strip('"')
        cookies_dict = {}

        # Split by the standard cookie separator "; "
        for cookie_pair in cookie_string.split('; '):
            # Find the first '=' which separates the name from the value
            if '=' in cookie_pair:
                name, value = cookie_pair.split('=', 1)
                # Store in the dictionary
                cookies_dict[name] = value

        return cookies_dict