from rest_framework import routers
from django.urls import path, include

from .api import DeveloperAccessStatusView, DeveloperQuotaStatusView, DeveloperTokenView, DeveloperUsageExportView, DeveloperUsageStatusView, GardenViewSet, PodViewSet, PodNoteViewSet, GlobalNoteViewSet

router = routers.DefaultRouter()
router.register(r'gardens', GardenViewSet, basename='garden')
router.register(r'pods', PodViewSet, basename='pod')
router.register(r'pod-notes', PodNoteViewSet, basename='pod-note')
router.register(r'global-notes', GlobalNoteViewSet, basename='global-note')

urlpatterns = [
    path('developer-access/', DeveloperAccessStatusView.as_view(), name='developer-access-status'),
    path('developer-quota/', DeveloperQuotaStatusView.as_view(), name='developer-quota-status'),
    path('developer-usage/', DeveloperUsageStatusView.as_view(), name='developer-usage-status'),
    path('developer-usage/export/', DeveloperUsageExportView.as_view(), name='developer-usage-export'),
    path('developer-token/', DeveloperTokenView.as_view(), name='developer-token'),
    path('', include(router.urls)),
]
