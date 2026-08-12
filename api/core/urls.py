from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from iam.views import JWKSView


urlpatterns = [
    # path('admin/', admin.site.urls),
    path('.well-known/jwks.json', JWKSView.as_view(), name='jwks'),
    path('api/iam/', include('iam.urls')),
    path('api/users/', include('users.urls')),
]

# Conditionally include Swagger UI only in development
from django.conf import settings

if settings.DEBUG:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/schema/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    ]