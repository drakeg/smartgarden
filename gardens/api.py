from django.conf import settings
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from .models import DeveloperAccess, Garden, GlobalNote, Pod, PodNote
from .serializers import GardenSerializer, GlobalNoteSerializer, PodNoteSerializer, PodSerializer


class HasDeveloperApiAccess(permissions.BasePermission):
    message = "An active developer API plan is required."

    def has_permission(self, request, view):
        if not settings.API_PAYWALL_ENABLED:
            return True

        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True

        try:
            access = user.developer_access
        except DeveloperAccess.DoesNotExist:
            return False
        return access.has_access()


class IsGardenOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and obj.owner_id == request.user.id


class IsPodGardenOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_authenticated
            and obj.garden.owner_id == request.user.id
            and not obj.garden.is_guest
        )


class IsPodNoteGardenOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_authenticated
            and obj.pod.garden.owner_id == request.user.id
            and not obj.pod.garden.is_guest
        )


class IsGlobalNoteAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and obj.author_id == request.user.id


class GardenViewSet(viewsets.ModelViewSet):
    serializer_class = GardenSerializer
    permission_classes = [permissions.IsAuthenticated, HasDeveloperApiAccess, IsGardenOwner]
    filterset_fields = ['device_type', 'is_public']
    search_fields = ['name', 'share_slug']

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Garden.objects.none()
        return Garden.objects.filter(
            owner=self.request.user,
            is_guest=False,
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, is_guest=False, guest_token='')


class PodViewSet(viewsets.ModelViewSet):
    serializer_class = PodSerializer
    permission_classes = [permissions.IsAuthenticated, HasDeveloperApiAccess, IsPodGardenOwner]
    filterset_fields = ['garden', 'position', 'status']
    search_fields = ['plant_name']

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Pod.objects.none()
        return Pod.objects.filter(
            garden__owner=self.request.user,
            garden__is_guest=False,
        ).select_related('garden').order_by('garden', 'position')

    def perform_create(self, serializer):
        garden = serializer.validated_data['garden']
        if garden.owner_id != self.request.user.id or garden.is_guest:
            raise PermissionDenied('You can only add pods to your own account gardens.')
        serializer.save()


class PodNoteViewSet(viewsets.ModelViewSet):
    serializer_class = PodNoteSerializer
    permission_classes = [permissions.IsAuthenticated, HasDeveloperApiAccess, IsPodNoteGardenOwner]
    filterset_fields = ['pod__garden', 'pod__position']
    search_fields = ['note']

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PodNote.objects.none()
        return PodNote.objects.filter(
            pod__garden__owner=self.request.user,
            pod__garden__is_guest=False,
        ).select_related('pod__garden').order_by('-created_at')

    def perform_create(self, serializer):
        pod = serializer.validated_data['pod']
        if pod.garden.owner_id != self.request.user.id or pod.garden.is_guest:
            raise PermissionDenied('You can only add notes to pods in your own account gardens.')
        serializer.save()


class GlobalNoteViewSet(viewsets.ModelViewSet):
    queryset = GlobalNote.objects.all().order_by('-created_at')
    serializer_class = GlobalNoteSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, HasDeveloperApiAccess, IsGlobalNoteAuthorOrReadOnly]
    filterset_fields = ['author__username']
    search_fields = ['title', 'note', 'author__username']

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
