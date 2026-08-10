from django.urls import path
from users.views import LoginView, RefreshTokenView, UserStatusView


urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('status/', UserStatusView.as_view(), name='user-status'),
    # ... other user-related endpoints
]