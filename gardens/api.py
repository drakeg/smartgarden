from django.conf import settings
from django.core.cache import caches
from django.db.models import F, Sum
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta
import csv
import math
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.exceptions import PermissionDenied
from rest_framework.authtoken.models import Token

from .models import DeveloperAccess, DeveloperApiUsageDaily, Garden, GlobalNote, Pod, PodNote
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


class DeveloperUsageStatusView(APIView):
    """Return durable daily Developer API usage for the signed-in user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            days = int(request.query_params.get('days', '30'))
        except ValueError:
            days = 30
        days = min(max(days, 1), 90)

        end_date = timezone.localdate()
        start_date = end_date - timedelta(days=days - 1)
        rows = list(
            DeveloperApiUsageDaily.objects.filter(
                user=request.user,
                usage_date__gte=start_date,
                usage_date__lte=end_date,
            ).order_by('usage_date', 'plan')
        )
        totals = DeveloperApiUsageDaily.objects.filter(
            user=request.user,
            usage_date__gte=start_date,
            usage_date__lte=end_date,
        ).aggregate(
            request_count=Sum('request_count'),
            success_count=Sum('success_count'),
            client_error_count=Sum('client_error_count'),
            server_error_count=Sum('server_error_count'),
        )

        return Response({
            'days': days,
            'start_date': start_date,
            'end_date': end_date,
            'request_count': totals['request_count'] or 0,
            'success_count': totals['success_count'] or 0,
            'client_error_count': totals['client_error_count'] or 0,
            'server_error_count': totals['server_error_count'] or 0,
            'durable': True,
            'billing_grade': False,
            'usage': [
                {
                    'date': row.usage_date,
                    'plan': row.plan,
                    'request_count': row.request_count,
                    'success_count': row.success_count,
                    'client_error_count': row.client_error_count,
                    'server_error_count': row.server_error_count,
                    'last_request_at': row.last_request_at,
                }
                for row in rows
            ],
        })


class DeveloperUsageExportView(APIView):
    """Export the signed-in developer's durable usage history as CSV."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            days = int(request.query_params.get('days', '30'))
        except ValueError:
            days = 30
        days = min(max(days, 1), 90)

        end_date = timezone.localdate()
        start_date = end_date - timedelta(days=days - 1)
        rows = DeveloperApiUsageDaily.objects.filter(
            user=request.user,
            usage_date__gte=start_date,
            usage_date__lte=end_date,
        ).order_by('usage_date', 'plan')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="smartgarden-api-usage-{start_date}-to-{end_date}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow([
            'date',
            'plan',
            'request_count',
            'success_count',
            'client_error_count',
            'server_error_count',
            'last_request_at',
        ])
        for row in rows:
            writer.writerow([
                row.usage_date.isoformat(),
                row.plan,
                row.request_count,
                row.success_count,
                row.client_error_count,
                row.server_error_count,
                row.last_request_at.isoformat() if row.last_request_at else '',
            ])

        return response


class DeveloperUsageMeteringMixin:
    """Persist daily aggregates for accepted paid Developer API requests."""

    excluded_metering_statuses = {401, 403, 429}

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        self._record_developer_usage(request, response)
        return response

    def _record_developer_usage(self, request, response):
        if not settings.API_PAYWALL_ENABLED:
            return

        user = request.user
        if not user or not user.is_authenticated or user.is_staff or user.is_superuser:
            return
        if response.status_code in self.excluded_metering_statuses:
            return

        try:
            access = user.developer_access
        except DeveloperAccess.DoesNotExist:
            return
        if not access.has_access():
            return

        now = timezone.now()
        bucket, _ = DeveloperApiUsageDaily.objects.get_or_create(
            user=user,
            usage_date=timezone.localdate(now),
            plan=access.plan,
        )

        updates = {
            'request_count': F('request_count') + 1,
            'last_request_at': now,
        }
        if 200 <= response.status_code < 400:
            updates['success_count'] = F('success_count') + 1
        elif 400 <= response.status_code < 500:
            updates['client_error_count'] = F('client_error_count') + 1
        else:
            updates['server_error_count'] = F('server_error_count') + 1

        DeveloperApiUsageDaily.objects.filter(pk=bucket.pk).update(**updates)


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


class GardenViewSet(DeveloperUsageMeteringMixin, viewsets.ModelViewSet):
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


class PodViewSet(DeveloperUsageMeteringMixin, viewsets.ModelViewSet):
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


class PodNoteViewSet(DeveloperUsageMeteringMixin, viewsets.ModelViewSet):
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


class GlobalNoteViewSet(DeveloperUsageMeteringMixin, viewsets.ModelViewSet):
    queryset = GlobalNote.objects.all().order_by('-created_at')
    serializer_class = GlobalNoteSerializer
    throttle_classes = [DeveloperPlanRateThrottle]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, HasDeveloperApiAccess, IsGlobalNoteAuthorOrReadOnly]
    filterset_fields = ['author__username']
    search_fields = ['title', 'note', 'author__username']

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
