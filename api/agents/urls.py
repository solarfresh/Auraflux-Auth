from agents.views import (ModelProviderAvailableView, ModelProviderDetailView,
                          ModelProviderView)
from django.urls import path

urlpatterns = [
    path('models/', ModelProviderView.as_view(), name='model-provider'),
    path('models/available/', ModelProviderAvailableView.as_view(), name='model-available'),
    path('models/<uuid:provider_id>/', ModelProviderDetailView.as_view(), name='model-provider-detail'),
]
