from django.urls import path
from iam.views import (ClientCredentialsTokenView, RefreshTokenView,
                       ServiceRegisterView, TokenExchangeView)

urlpatterns = [
    path('services/', ServiceRegisterView.as_view(), name='service-register'),
    path('tokens/m2m/', ClientCredentialsTokenView.as_view(), name='token-m2m'),
    path('tokens/exchange/', TokenExchangeView.as_view(), name='token-exchange'),
    path('tokens/refresh/', RefreshTokenView.as_view(), name='token_refresh'),
]