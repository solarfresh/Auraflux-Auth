import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
# from realtime.routing import urlpatterns

# 1. Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django_asgi_app = get_asgi_application()

# Ensuring that the application setup and settings loading happen before
# importing any module that depends on the Django framework
# from auth.authentication import JWTAuthMiddleware

# 2. Get the ASGI application callable
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # "websocket": JWTAuthMiddleware(
    #     URLRouter(
    #         urlpatterns
    #     )
    # ),
})