from rest_framework import routers
from django.urls import path, include

from .api import DeveloperAccessStatusView, GardenViewSet, PodViewSet, PodNoteViewSet, GlobalNoteViewSet

router = routers.DefaultRouter()
router.register(r'gardens', GardenViewSet, basename='garden')
router.register(r'pods', PodViewSet, basename='pod')
router.register(r'pod-notes', PodNoteViewSet, basename='pod-note')
router.register(r'global-notes', GlobalNoteViewSet, basename='global-note')

urlpatterns = [
    path('developer-access/', DeveloperAccessStatusView.as_view(), name='developer-access-status'),
    path('', include(router.urls)),
]
