from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Garden, Pod, PodNote, GlobalNote
from .serializers import GardenSerializer, PodSerializer, PodNoteSerializer, GlobalNoteSerializer


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Read-only allowed
        if request.method in permissions.SAFE_METHODS:
            return True
        # For gardens and pods, check owner if available
        owner = getattr(obj, 'owner', None)
        if owner is None:
            return request.user.is_authenticated
        return request.user.is_authenticated and obj.owner_id == request.user.id


class GardenViewSet(viewsets.ModelViewSet):
    queryset = Garden.objects.all().order_by('-created_at')
    serializer_class = GardenSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PodViewSet(viewsets.ModelViewSet):
    queryset = Pod.objects.all().order_by('garden', 'position')
    serializer_class = PodSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class PodNoteViewSet(viewsets.ModelViewSet):
    queryset = PodNote.objects.all().order_by('-created_at')
    serializer_class = PodNoteSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class GlobalNoteViewSet(viewsets.ModelViewSet):
    queryset = GlobalNote.objects.all().order_by('-created_at')
    serializer_class = GlobalNoteSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user if self.request.user.is_authenticated else None)
