from django.conf import settings
from django.core.cache import caches
import math
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.exceptions import PermissionDenied
from rest_framework.authtoken.models import Token

from .models import DeveloperAccess, Garden, GlobalNote, Pod, PodNote
from .serializers import GardenSerializer, GlobalNoteSerializer, PodNoteSerializer, PodSerializer


class DeveloperPlanRateThrottle(SimpleRateThrottle):
    """Apply per-user request limits based on the active developer plan."""

    scope = 'developer-plan'

    def __init__(self):
        self.cache = caches['developer_api']
        self.rate = None
        self.num_requests = None
        self.duration = None

    def allow_request(self, request, view):
        if not settings.API_PAYWALL_ENABLED:
            return True

        user = request.user
        if not user.is_authenticated or user.is_staff or user.is_superuser:
            return True

        try:
            access = user.developer_access
        except DeveloperAccess.DoesNotExist:
            return True

        if not access.has_access():
            return True

        rate = settings.API_PLAN_THROTTLE_RATES.get(access.plan)
        if not rate:
            return True

        self.rate = rate
        self.num_requests, self.duration = self.parse_rate(rate)
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        user = request.user
        try:
            plan = user.developer_access.plan.lower()
        except DeveloperAccess.DoesNotExist:
            return None
        return self.cache_format % {
            'scope': f'{self.scope}-{plan}',
            'ident': str(user.pk),
        }


class DeveloperAccessStatusView(APIView):
    """Return the signed-in developer's effective API access state."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        admin_bypass = bool(user.is_staff or user.is_superuser)

        try:
            access = user.developer_access
        except DeveloperAccess.DoesNotExist:
            access = None

        entitlement_active = bool(access and access.has_access())
        paywall_enabled = bool(settings.API_PAYWALL_ENABLED)
        effective_access = (not paywall_enabled) or admin_bypass or entitlement_active
        request_rate = None
        if paywall_enabled and entitlement_active and not admin_bypass:
            request_rate = settings.API_PLAN_THROTTLE_RATES.get(access.plan)

        return Response({
            'paywall_enabled': paywall_enabled,
            'entitlement_present': access is not None,
            'entitlement_active': entitlement_active,
            'effective_access': effective_access,
            'admin_bypass': admin_bypass,
            'plan': access.plan if access else None,
            'status': access.status if access else None,
            'access_expires_at': access.access_expires_at if access else None,
            'request_rate': request_rate,
        })


class DeveloperQuotaStatusView(APIView):
    """Return the caller's approximate current developer API rate-window usage."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        admin_bypass = bool(user.is_staff or user.is_superuser)

        try:
            access = user.developer_access
        except DeveloperAccess.DoesNotExist:
            access = None

        paywall_enabled = bool(settings.API_PAYWALL_ENABLED)
        entitlement_active = bool(access and access.has_access())
        quota_applicable = (
            paywall_enabled
            and entitlement_active
            and not admin_bypass
        )

        response = {
            'paywall_enabled': paywall_enabled,
            'quota_applicable': quota_applicable,
            'admin_bypass': admin_bypass,
            'plan': access.plan if access else None,
            'request_rate': None,
            'limit': None,
            'used': None,
            'remaining': None,
            'window_seconds': None,
            'retry_after_seconds': None,
            'approximate': True,
        }

        if not quota_applicable:
            return Response(response)

        rate = settings.API_PLAN_THROTTLE_RATES.get(access.plan)
        if not rate:
            return Response(response)

        throttle = DeveloperPlanRateThrottle()
        throttle.rate = rate
        throttle.num_requests, throttle.duration = throttle.parse_rate(rate)

        key = throttle.cache_format % {
            'scope': f'{throttle.scope}-{access.plan.lower()}',
            'ident': str(user.pk),
        }
        now = throttle.timer()
        history = throttle.cache.get(key, [])
        active_history = [
            timestamp
            for timestamp in history
            if timestamp > now - throttle.duration
        ]

        used = len(active_history)
        remaining = max(throttle.num_requests - used, 0)
        retry_after_seconds = None
        if remaining == 0 and active_history:
            retry_after_seconds = max(
                0,
                math.ceil(active_history[-1] + throttle.duration - now),
            )

        response.update({
            'request_rate': rate,
            'limit': throttle.num_requests,
            'used': used,
            'remaining': remaining,
            'window_seconds': int(throttle.duration),
            'retry_after_seconds': retry_after_seconds,
        })
        return Response(response)


class DeveloperTokenView(APIView):
    """Inspect, rotate, or revoke the signed-in user's DRF API token."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        token = Token.objects.filter(user=request.user).first()
        return Response({
            'has_token': token is not None,
            'created_at': token.created if token else None,
        })

    def post(self, request):
        password = request.data.get('password', '')
        if not password or not request.user.check_password(password):
            raise PermissionDenied('Password confirmation failed.')

        Token.objects.filter(user=request.user).delete()
        token = Token.objects.create(user=request.user)
        return Response({
            'token': token.key,
            'created_at': token.created,
            'rotated': True,
        })

    def delete(self, request):
        password = request.data.get('password', '')
        if not password or not request.user.check_password(password):
            raise PermissionDenied('Password confirmation failed.')

        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
    throttle_classes = [DeveloperPlanRateThrottle]
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
    throttle_classes = [DeveloperPlanRateThrottle]
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

    def perform_update(self, serializer):
        garden = serializer.validated_data.get('garden', serializer.instance.garden)
        if garden.owner_id != self.request.user.id or garden.is_guest:
            raise PermissionDenied('You can only move pods within your own account gardens.')
        serializer.save()


class PodNoteViewSet(viewsets.ModelViewSet):
    serializer_class = PodNoteSerializer
    throttle_classes = [DeveloperPlanRateThrottle]
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

    def perform_update(self, serializer):
        pod = serializer.validated_data.get('pod', serializer.instance.pod)
        if pod.garden.owner_id != self.request.user.id or pod.garden.is_guest:
            raise PermissionDenied('You can only move notes within your own account gardens.')
        serializer.save()


class GlobalNoteViewSet(viewsets.ModelViewSet):
    queryset = GlobalNote.objects.all().order_by('-created_at')
    serializer_class = GlobalNoteSerializer
    throttle_classes = [DeveloperPlanRateThrottle]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, HasDeveloperApiAccess, IsGlobalNoteAuthorOrReadOnly]
    filterset_fields = ['author__username']
    search_fields = ['title', 'note', 'author__username']

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
