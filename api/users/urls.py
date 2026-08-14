from django.urls import path
from users.views import LoginView, UserStatusView


urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('status/', UserStatusView.as_view(), name='user-status'),
    # ... other user-related endpoints
]