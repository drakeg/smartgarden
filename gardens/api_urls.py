from rest_framework import routers
from django.urls import path, include

from .api import GardenViewSet, PodViewSet, PodNoteViewSet, GlobalNoteViewSet

router = routers.DefaultRouter()
router.register(r'gardens', GardenViewSet)
router.register(r'pods', PodViewSet)
router.register(r'pod-notes', PodNoteViewSet)
router.register(r'global-notes', GlobalNoteViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
