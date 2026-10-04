from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache, caches
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token

from .models import DeveloperAccess, DeveloperAccessStatus, DeveloperApiUsageDaily, DeveloperPlan, Garden, GlobalNote, Pod

user_model = get_user_model()


class ApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = user_model.objects.create_user(username='apiuser', password='pass')
        self.token, _ = Token.objects.get_or_create(user=self.user)

    def test_obtain_token_and_create_global_note(self):
        # Ensure token exists and can be used to auth
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        resp = self.client.post('/api/global-notes/', {'title': 'API Tip', 'note': 'Avoid north windows'})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(GlobalNote.objects.count(), 1)

    def test_global_notes_list_readable_anonymously(self):
        GlobalNote.objects.create(title='Public', note='Visible')
        resp = self.client.get('/api/global-notes/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('results', resp.json())

    def test_create_requires_auth(self):
        # clear credentials
        self.client.credentials()
        resp = self.client.post('/api/global-notes/', {'title': 'NoAuth', 'note': 'Should fail'})
        self.assertIn(resp.status_code, (401, 403))

    def test_gardens_filtering_and_search_are_owner_scoped(self):
        other = user_model.objects.create_user(username='other', password='pass')
        Garden.objects.create(owner=self.user, name='Alpha Garden', device_type='AHOPEGARDEN_12', is_public=True)
        Garden.objects.create(owner=other, name='Beta Garden', device_type='AHOPEGARDEN_12', is_public=False)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        resp = self.client.get('/api/gardens/?is_public=true')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual([item['name'] for item in data.get('results', [])], ['Alpha Garden'])

        resp = self.client.get('/api/gardens/?search=Beta')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get('results', []), [])

    def test_garden_pod_and_note_apis_require_authentication(self):
        garden = Garden.objects.create(owner=self.user, name='Private')
        pod = garden.pods.create(position=1)
        note = pod.notes.create(note='Private note')

        self.client.credentials()
        for url in (
            '/api/gardens/',
            f'/api/gardens/{garden.id}/',
            '/api/pods/',
            f'/api/pods/{pod.id}/',
            '/api/pod-notes/',
            f'/api/pod-notes/{note.id}/',
        ):
            resp = self.client.get(url)
            self.assertIn(resp.status_code, (401, 403))

    def test_authenticated_user_cannot_read_or_modify_other_users_garden_data(self):
        other = user_model.objects.create_user(username='apiother', password='pass')
        other_garden = Garden.objects.create(owner=other, name='Other Private')
        other_pod = other_garden.pods.create(position=1, plant_name='Secret Basil')
        other_note = other_pod.notes.create(note='Secret note')

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        list_resp = self.client.get('/api/gardens/')
        self.assertEqual(list_resp.status_code, 200)
        self.assertFalse(any(item['name'] == 'Other Private' for item in list_resp.json().get('results', [])))

        for url in (
            f'/api/gardens/{other_garden.id}/',
            f'/api/pods/{other_pod.id}/',
            f'/api/pod-notes/{other_note.id}/',
        ):
            get_resp = self.client.get(url)
            patch_resp = self.client.patch(url, {'note': 'changed'}, format='json')
            delete_resp = self.client.delete(url)
            self.assertEqual(get_resp.status_code, 404)
            self.assertEqual(patch_resp.status_code, 404)
            self.assertEqual(delete_resp.status_code, 404)

    def test_cannot_create_pod_or_note_under_other_users_garden(self):
        other = user_model.objects.create_user(username='apiother2', password='pass')
        other_garden = Garden.objects.create(owner=other, name='Other Garden')
        other_pod = other_garden.pods.create(position=1)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        pod_resp = self.client.post('/api/pods/', {
            'garden': other_garden.id,
            'position': 2,
            'plant_name': 'Injected',
            'status': 'EMPTY',
        }, format='json')
        self.assertEqual(pod_resp.status_code, 403)

        note_resp = self.client.post('/api/pod-notes/', {
            'pod': other_pod.id,
            'note': 'Injected note',
        }, format='json')
        self.assertEqual(note_resp.status_code, 403)

    def test_pod_reparenting_rejects_other_users_and_guest_gardens(self):
        other = user_model.objects.create_user(username='moveother', password='pass')
        source = Garden.objects.create(owner=self.user, name='Source')
        target = Garden.objects.create(owner=self.user, name='Target')
        foreign = Garden.objects.create(owner=other, name='Foreign')
        guest = Garden.objects.create(is_guest=True, guest_token='guest-move', name='Guest')
        pod = source.pods.create(position=1, plant_name='Basil')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        for garden in (foreign, guest):
            resp = self.client.patch(
                f'/api/pods/{pod.id}/', {'garden': garden.id}, format='json',
            )
            self.assertEqual(resp.status_code, 403)
            pod.refresh_from_db()
            self.assertEqual(pod.garden_id, source.id)

        resp = self.client.patch(
            f'/api/pods/{pod.id}/',
            {'garden': target.id, 'plant_name': 'Moved basil'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        pod.refresh_from_db()
        self.assertEqual(pod.garden_id, target.id)
        self.assertEqual(pod.plant_name, 'Moved basil')

    def test_pod_note_reparenting_rejects_other_users_and_guest_gardens(self):
        other = user_model.objects.create_user(username='noteothermove', password='pass')
        source = Garden.objects.create(owner=self.user, name='Source')
        target = Garden.objects.create(owner=self.user, name='Target')
        foreign = Garden.objects.create(owner=other, name='Foreign')
        guest = Garden.objects.create(is_guest=True, guest_token='guest-note-move', name='Guest')
        original_pod = source.pods.create(position=1)
        own_pod = target.pods.create(position=1)
        foreign_pod = foreign.pods.create(position=1)
        guest_pod = guest.pods.create(position=1)
        note = original_pod.notes.create(note='Private history')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        for pod in (foreign_pod, guest_pod):
            resp = self.client.patch(
                f'/api/pod-notes/{note.id}/', {'pod': pod.id}, format='json',
            )
            self.assertEqual(resp.status_code, 403)
            note.refresh_from_db()
            self.assertEqual(note.pod_id, original_pod.id)

        resp = self.client.patch(
            f'/api/pod-notes/{note.id}/',
            {'pod': own_pod.id, 'note': 'Moved history'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.pod_id, own_pod.id)
        self.assertEqual(note.note, 'Moved history')

    def test_global_note_update_and_delete_are_author_only(self):
        other = user_model.objects.create_user(username='noteother', password='pass')
        note = GlobalNote.objects.create(author=other, title='Other', note='Read only')

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        get_resp = self.client.get(f'/api/global-notes/{note.id}/')
        patch_resp = self.client.patch(
            f'/api/global-notes/{note.id}/',
            {'title': 'Hijacked'},
            format='json',
        )
        delete_resp = self.client.delete(f'/api/global-notes/{note.id}/')

        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(patch_resp.status_code, 403)
        self.assertEqual(delete_resp.status_code, 403)
        note.refresh_from_db()
        self.assertEqual(note.title, 'Other')

    @override_settings(API_PAYWALL_ENABLED=True)
    def test_developer_paywall_blocks_authenticated_user_without_entitlement(self):
        Garden.objects.create(owner=self.user, name='Paywalled Garden')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        resp = self.client.get('/api/gardens/')

        self.assertEqual(resp.status_code, 403)
        self.assertIn('active developer api plan', resp.json()['detail'].lower())

    @override_settings(API_PAYWALL_ENABLED=True)
    def test_active_developer_entitlement_allows_api_access(self):
        DeveloperAccess.objects.create(
            user=self.user,
            status=DeveloperAccessStatus.ACTIVE,
        )
        Garden.objects.create(owner=self.user, name='Developer Garden')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        resp = self.client.get('/api/gardens/')

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(any(item['name'] == 'Developer Garden' for item in resp.json().get('results', [])))

    @override_settings(API_PAYWALL_ENABLED=True)
    def test_expired_or_past_due_developer_entitlement_is_denied(self):
        access = DeveloperAccess.objects.create(
            user=self.user,
            status=DeveloperAccessStatus.ACTIVE,
            access_expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        expired_resp = self.client.get('/api/gardens/')
        self.assertEqual(expired_resp.status_code, 403)

        access.access_expires_at = None
        access.status = DeveloperAccessStatus.PAST_DUE
        access.save(update_fields=['access_expires_at', 'status'])

        past_due_resp = self.client.get('/api/gardens/')
        self.assertEqual(past_due_resp.status_code, 403)

    @override_settings(API_PAYWALL_ENABLED=True)
    def test_staff_bypasses_developer_paywall(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        resp = self.client.get('/api/gardens/')

        self.assertEqual(resp.status_code, 200)

    @override_settings(API_PAYWALL_ENABLED=True)
    def test_paywall_covers_public_global_notes_api(self):
        GlobalNote.objects.create(title='Public', note='Web-visible')
        self.client.credentials()

        resp = self.client.get('/api/global-notes/')

        self.assertIn(resp.status_code, (401, 403))

    @override_settings(
        API_PAYWALL_ENABLED=True,
        API_PLAN_THROTTLE_RATES={
            'STARTER': '2/minute',
            'PRO': '4/minute',
            'ENTERPRISE': '6/minute',
        },
    )
    def test_starter_plan_is_throttled_at_configured_limit(self):
        cache.clear()
        DeveloperAccess.objects.create(
            user=self.user,
            plan=DeveloperPlan.STARTER,
            status=DeveloperAccessStatus.ACTIVE,
        )
        Garden.objects.create(owner=self.user, name='Rate Limited')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.assertEqual(self.client.get('/api/gardens/').status_code, 200)
        self.assertEqual(self.client.get('/api/gardens/').status_code, 200)
        limited = self.client.get('/api/gardens/')

        self.assertEqual(limited.status_code, 429)

    @override_settings(
        API_PAYWALL_ENABLED=True,
        API_PLAN_THROTTLE_RATES={
            'STARTER': '1/minute',
            'PRO': '3/minute',
            'ENTERPRISE': '5/minute',
        },
    )
    def test_pro_plan_allows_more_requests_than_starter(self):
        cache.clear()
        access = DeveloperAccess.objects.create(
            user=self.user,
            plan=DeveloperPlan.PRO,
            status=DeveloperAccessStatus.ACTIVE,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        for _ in range(3):
            self.assertEqual(self.client.get('/api/gardens/').status_code, 200)
        self.assertEqual(self.client.get('/api/gardens/').status_code, 429)

        cache.clear()
        access.plan = DeveloperPlan.STARTER
        access.save(update_fields=['plan'])
        self.assertEqual(self.client.get('/api/gardens/').status_code, 200)
        self.assertEqual(self.client.get('/api/gardens/').status_code, 429)

    @override_settings(
        API_PAYWALL_ENABLED=True,
        API_PLAN_THROTTLE_RATES={
            'STARTER': '1/minute',
            'PRO': '1/minute',
            'ENTERPRISE': '1/minute',
        },
    )
    def test_staff_bypasses_developer_rate_limits(self):
        cache.clear()
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        DeveloperAccess.objects.create(
            user=self.user,
            status=DeveloperAccessStatus.ACTIVE,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        for _ in range(3):
            self.assertEqual(self.client.get('/api/gardens/').status_code, 200)

    @override_settings(
        API_PAYWALL_ENABLED=False,
        API_PLAN_THROTTLE_RATES={
            'STARTER': '1/minute',
            'PRO': '1/minute',
            'ENTERPRISE': '1/minute',
        },
    )
    def test_rate_limits_are_disabled_with_paywall(self):
        cache.clear()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        for _ in range(3):
            self.assertEqual(self.client.get('/api/gardens/').status_code, 200)

    @override_settings(
        API_PAYWALL_ENABLED=True,
        API_PLAN_THROTTLE_RATES={
            'STARTER': '2/minute',
            'PRO': '4/minute',
            'ENTERPRISE': '6/minute',
        },
    )
    def test_rate_limit_is_shared_across_api_endpoints(self):
        caches['developer_api'].clear()
        DeveloperAccess.objects.create(
            user=self.user, status=DeveloperAccessStatus.ACTIVE,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.assertEqual(self.client.get('/api/gardens/').status_code, 200)
        self.assertEqual(self.client.get('/api/pods/').status_code, 200)
        self.assertEqual(self.client.get('/api/pod-notes/').status_code, 429)

    @override_settings(API_PAYWALL_ENABLED=True)
    def test_developer_throttle_uses_dedicated_cache_alias(self):
        from .api import DeveloperPlanRateThrottle

        throttle = DeveloperPlanRateThrottle()
        self.assertIs(throttle.cache, caches['developer_api'])

    def test_developer_access_status_requires_authentication(self):
        self.client.credentials()
        resp = self.client.get('/api/developer-access/')
        self.assertIn(resp.status_code, (401, 403))

    @override_settings(API_PAYWALL_ENABLED=True)
    def test_developer_access_status_reports_missing_entitlement(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        resp = self.client.get('/api/developer-access/')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['paywall_enabled'])
        self.assertFalse(data['entitlement_present'])
        self.assertFalse(data['entitlement_active'])
        self.assertFalse(data['effective_access'])
        self.assertIsNone(data['plan'])
        self.assertIsNone(data['status'])
        self.assertIsNone(data['request_rate'])

    @override_settings(
        API_PAYWALL_ENABLED=True,
        API_PLAN_THROTTLE_RATES={
            'STARTER': '100/hour',
            'PRO': '1000/hour',
            'ENTERPRISE': '5000/hour',
        },
    )
    def test_developer_access_status_reports_active_plan_and_rate(self):
        access = DeveloperAccess.objects.create(
            user=self.user,
            plan=DeveloperPlan.PRO,
            status=DeveloperAccessStatus.ACTIVE,
            billing_provider='example-payments',
            billing_customer_id='customer-secret',
            billing_subscription_id='subscription-secret',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        resp = self.client.get('/api/developer-access/')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['entitlement_present'])
        self.assertTrue(data['entitlement_active'])
        self.assertTrue(data['effective_access'])
        self.assertEqual(data['plan'], DeveloperPlan.PRO)
        self.assertEqual(data['status'], DeveloperAccessStatus.ACTIVE)
        self.assertEqual(data['request_rate'], '1000/hour')
        self.assertNotIn('billing_provider', data)
        self.assertNotIn('billing_customer_id', data)
        self.assertNotIn('billing_subscription_id', data)
        self.assertEqual(access.user_id, self.user.id)

    @override_settings(API_PAYWALL_ENABLED=True)
    def test_developer_access_status_reports_expired_entitlement(self):
        DeveloperAccess.objects.create(
            user=self.user,
            status=DeveloperAccessStatus.ACTIVE,
            access_expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        resp = self.client.get('/api/developer-access/')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['entitlement_present'])
        self.assertFalse(data['entitlement_active'])
        self.assertFalse(data['effective_access'])
        self.assertIsNone(data['request_rate'])

    @override_settings(API_PAYWALL_ENABLED=False)
    def test_developer_access_status_reflects_disabled_paywall(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        resp = self.client.get('/api/developer-access/')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data['paywall_enabled'])
        self.assertTrue(data['effective_access'])
        self.assertIsNone(data['request_rate'])

    @override_settings(API_PAYWALL_ENABLED=True)
    def test_developer_access_status_reports_staff_bypass(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        resp = self.client.get('/api/developer-access/')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['admin_bypass'])
        self.assertTrue(data['effective_access'])
        self.assertIsNone(data['request_rate'])

    def test_developer_quota_status_requires_authentication(self):
        self.client.credentials()
        resp = self.client.get('/api/developer-quota/')
        self.assertIn(resp.status_code, (401, 403))

    @override_settings(API_PAYWALL_ENABLED=True)
    def test_developer_quota_status_without_active_entitlement_is_not_applicable(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        resp = self.client.get('/api/developer-quota/')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data['quota_applicable'])
        self.assertIsNone(data['used'])
        self.assertIsNone(data['remaining'])
        self.assertTrue(data['approximate'])

    @override_settings(
        API_PAYWALL_ENABLED=True,
        API_PLAN_THROTTLE_RATES={
            'STARTER': '2/minute',
            'PRO': '4/minute',
            'ENTERPRISE': '6/minute',
        },
    )
    def test_developer_quota_reports_current_shared_throttle_usage(self):
        caches['developer_api'].clear()
        DeveloperAccess.objects.create(
            user=self.user,
            plan=DeveloperPlan.STARTER,
            status=DeveloperAccessStatus.ACTIVE,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        first = self.client.get('/api/gardens/')
        self.assertEqual(first.status_code, 200)

        quota = self.client.get('/api/developer-quota/')
        self.assertEqual(quota.status_code, 200)
        data = quota.json()
        self.assertTrue(data['quota_applicable'])
        self.assertEqual(data['request_rate'], '2/minute')
        self.assertEqual(data['limit'], 2)
        self.assertEqual(data['used'], 1)
        self.assertEqual(data['remaining'], 1)
        self.assertEqual(data['window_seconds'], 60)
        self.assertIsNone(data['retry_after_seconds'])

        second = self.client.get('/api/gardens/')
        self.assertEqual(second.status_code, 200)

        exhausted = self.client.get('/api/developer-quota/').json()
        self.assertEqual(exhausted['used'], 2)
        self.assertEqual(exhausted['remaining'], 0)
        self.assertGreaterEqual(exhausted['retry_after_seconds'], 1)
        self.assertLessEqual(exhausted['retry_after_seconds'], 60)

        rejected = self.client.get('/api/gardens/')
        self.assertEqual(rejected.status_code, 429)

        after_reject = self.client.get('/api/developer-quota/').json()
        self.assertEqual(after_reject['used'], 2)
        self.assertEqual(after_reject['remaining'], 0)

    @override_settings(API_PAYWALL_ENABLED=False)
    def test_developer_quota_is_not_applicable_when_paywall_is_disabled(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        data = self.client.get('/api/developer-quota/').json()

        self.assertFalse(data['paywall_enabled'])
        self.assertFalse(data['quota_applicable'])
        self.assertIsNone(data['request_rate'])

    @override_settings(API_PAYWALL_ENABLED=True)
    def test_developer_quota_reports_staff_bypass(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        DeveloperAccess.objects.create(
            user=self.user,
            status=DeveloperAccessStatus.ACTIVE,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        data = self.client.get('/api/developer-quota/').json()

        self.assertTrue(data['admin_bypass'])
        self.assertFalse(data['quota_applicable'])
        self.assertIsNone(data['used'])

    def test_developer_usage_status_requires_authentication(self):
        self.client.credentials()
        resp = self.client.get('/api/developer-usage/')
        self.assertIn(resp.status_code, (401, 403))

    @override_settings(
        API_PAYWALL_ENABLED=True,
        API_PLAN_THROTTLE_RATES={
            'STARTER': '10/minute',
            'PRO': '20/minute',
            'ENTERPRISE': '30/minute',
        },
    )
    def test_paid_api_requests_are_recorded_in_durable_daily_usage(self):
        DeveloperAccess.objects.create(
            user=self.user,
            plan=DeveloperPlan.STARTER,
            status=DeveloperAccessStatus.ACTIVE,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        ok = self.client.get('/api/gardens/')
        bad = self.client.post('/api/gardens/', {}, format='json')

        self.assertEqual(ok.status_code, 200)
        self.assertEqual(bad.status_code, 400)

        usage = DeveloperApiUsageDaily.objects.get(
            user=self.user,
            usage_date=timezone.localdate(),
            plan=DeveloperPlan.STARTER,
        )
        self.assertEqual(usage.request_count, 2)
        self.assertEqual(usage.success_count, 1)
        self.assertEqual(usage.client_error_count, 1)
        self.assertEqual(usage.server_error_count, 0)
        self.assertIsNotNone(usage.last_request_at)

    @override_settings(
        API_PAYWALL_ENABLED=True,
        API_PLAN_THROTTLE_RATES={
            'STARTER': '1/minute',
            'PRO': '20/minute',
            'ENTERPRISE': '30/minute',
        },
    )
    def test_throttled_requests_are_not_added_to_durable_usage(self):
        caches['developer_api'].clear()
        DeveloperAccess.objects.create(
            user=self.user,
            plan=DeveloperPlan.STARTER,
            status=DeveloperAccessStatus.ACTIVE,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.assertEqual(self.client.get('/api/gardens/').status_code, 200)
        self.assertEqual(self.client.get('/api/gardens/').status_code, 429)

        usage = DeveloperApiUsageDaily.objects.get(user=self.user)
        self.assertEqual(usage.request_count, 1)
        self.assertEqual(usage.success_count, 1)

    @override_settings(API_PAYWALL_ENABLED=False)
    def test_durable_usage_is_not_recorded_when_paywall_is_disabled(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        resp = self.client.get('/api/gardens/')

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(DeveloperApiUsageDaily.objects.filter(user=self.user).exists())

    @override_settings(
        API_PAYWALL_ENABLED=True,
        API_PLAN_THROTTLE_RATES={
            'STARTER': '10/minute',
            'PRO': '20/minute',
            'ENTERPRISE': '30/minute',
        },
    )
    def test_usage_plan_is_snapshotted_when_plan_changes(self):
        access = DeveloperAccess.objects.create(
            user=self.user,
            plan=DeveloperPlan.STARTER,
            status=DeveloperAccessStatus.ACTIVE,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.assertEqual(self.client.get('/api/gardens/').status_code, 200)

        access.plan = DeveloperPlan.PRO
        access.save(update_fields=['plan'])
        self.assertEqual(self.client.get('/api/gardens/').status_code, 200)

        buckets = DeveloperApiUsageDaily.objects.filter(
            user=self.user,
            usage_date=timezone.localdate(),
        ).order_by('plan')
        self.assertEqual(buckets.count(), 2)
        self.assertEqual(
            {bucket.plan: bucket.request_count for bucket in buckets},
            {DeveloperPlan.STARTER: 1, DeveloperPlan.PRO: 1},
        )

    def test_developer_usage_status_reports_durable_history_and_bounds_days(self):
        today = timezone.localdate()
        DeveloperApiUsageDaily.objects.create(
            user=self.user,
            usage_date=today,
            plan=DeveloperPlan.PRO,
            request_count=5,
            success_count=4,
            client_error_count=1,
        )
        DeveloperApiUsageDaily.objects.create(
            user=self.user,
            usage_date=today - timedelta(days=4),
            plan=DeveloperPlan.STARTER,
            request_count=3,
            success_count=3,
        )
        DeveloperApiUsageDaily.objects.create(
            user=self.user,
            usage_date=today - timedelta(days=40),
            plan=DeveloperPlan.STARTER,
            request_count=99,
            success_count=99,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        resp = self.client.get('/api/developer-usage/?days=7')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['days'], 7)
        self.assertEqual(data['request_count'], 8)
        self.assertEqual(data['success_count'], 7)
        self.assertEqual(data['client_error_count'], 1)
        self.assertTrue(data['durable'])
        self.assertFalse(data['billing_grade'])
        self.assertEqual(len(data['usage']), 2)

        bounded = self.client.get('/api/developer-usage/?days=999').json()
        self.assertEqual(bounded['days'], 90)

        invalid = self.client.get('/api/developer-usage/?days=not-a-number').json()
        self.assertEqual(invalid['days'], 30)

    def test_developer_usage_csv_export_requires_authentication(self):
        self.client.credentials()
        resp = self.client.get('/api/developer-usage/export/')
        self.assertIn(resp.status_code, (401, 403))

    def test_developer_usage_csv_export_is_owner_scoped_and_bounded(self):
        today = timezone.localdate()
        other = user_model.objects.create_user(username='usage-other', password='pass')
        DeveloperApiUsageDaily.objects.create(
            user=self.user,
            usage_date=today,
            plan=DeveloperPlan.PRO,
            request_count=5,
            success_count=4,
            client_error_count=1,
        )
        DeveloperApiUsageDaily.objects.create(
            user=self.user,
            usage_date=today - timedelta(days=4),
            plan=DeveloperPlan.STARTER,
            request_count=3,
            success_count=3,
        )
        DeveloperApiUsageDaily.objects.create(
            user=self.user,
            usage_date=today - timedelta(days=40),
            plan=DeveloperPlan.STARTER,
            request_count=99,
            success_count=99,
        )
        DeveloperApiUsageDaily.objects.create(
            user=other,
            usage_date=today,
            plan=DeveloperPlan.ENTERPRISE,
            request_count=777,
            success_count=777,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        resp = self.client.get('/api/developer-usage/export/?days=7')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="smartgarden-api-usage-', resp['Content-Disposition'])

        content = resp.content.decode('utf-8')
        self.assertIn('date,plan,request_count,success_count,client_error_count,server_error_count,last_request_at', content)
        self.assertIn(',PRO,5,4,1,0,', content)
        self.assertIn(',STARTER,3,3,0,0,', content)
        self.assertNotIn(',STARTER,99,99,0,0,', content)
        self.assertNotIn(',ENTERPRISE,777,777,0,0,', content)

        bounded = self.client.get('/api/developer-usage/export/?days=999')
        self.assertIn(
            str(today - timedelta(days=89)),
            bounded['Content-Disposition'],
        )

    def test_developer_token_status_does_not_expose_existing_key(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        resp = self.client.get('/api/developer-token/')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['has_token'])
        self.assertIsNotNone(data['created_at'])
        self.assertNotIn('token', data)
        self.assertNotIn(self.token.key, resp.content.decode())

    def test_developer_token_rotation_requires_password_confirmation(self):
        old_key = self.token.key
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {old_key}')

        resp = self.client.post(
            '/api/developer-token/',
            {'password': 'wrong-password'},
            format='json',
        )

        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Token.objects.filter(user=self.user, key=old_key).exists())

    def test_developer_token_rotation_invalidates_old_token(self):
        old_key = self.token.key
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {old_key}')

        resp = self.client.post(
            '/api/developer-token/',
            {'password': 'pass'},
            format='json',
        )

        self.assertEqual(resp.status_code, 200)
        new_key = resp.json()['token']
        self.assertNotEqual(new_key, old_key)
        self.assertFalse(Token.objects.filter(key=old_key).exists())
        self.assertTrue(Token.objects.filter(user=self.user, key=new_key).exists())

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {old_key}')
        self.assertIn(self.client.get('/api/developer-access/').status_code, (401, 403))

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {new_key}')
        self.assertEqual(self.client.get('/api/developer-access/').status_code, 200)

    def test_developer_token_revocation_requires_password_and_invalidates_token(self):
        old_key = self.token.key
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {old_key}')

        denied = self.client.delete(
            '/api/developer-token/',
            {'password': 'wrong-password'},
            format='json',
        )
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(Token.objects.filter(user=self.user, key=old_key).exists())

        revoked = self.client.delete(
            '/api/developer-token/',
            {'password': 'pass'},
            format='json',
        )
        self.assertEqual(revoked.status_code, 204)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {old_key}')
        self.assertIn(self.client.get('/api/developer-access/').status_code, (401, 403))

    def test_developer_token_lifecycle_requires_authentication(self):
        self.client.credentials()

        self.assertIn(self.client.get('/api/developer-token/').status_code, (401, 403))
        self.assertIn(
            self.client.post('/api/developer-token/', {'password': 'pass'}, format='json').status_code,
            (401, 403),
        )
        self.assertIn(
            self.client.delete('/api/developer-token/', {'password': 'pass'}, format='json').status_code,
            (401, 403),
        )

    def test_openapi_schema_and_docs_available(self):
        # schema JSON
        resp = self.client.get('/api/schema/')
        self.assertEqual(resp.status_code, 200)
        # Some servers return a vendor content-type; ensure schema is present and non-empty
        self.assertTrue(resp.content and len(resp.content) > 0)
        self.assertIn('openapi', resp.headers.get('Content-Type', '').lower())

        # swagger UI
        resp = self.client.get('/api/docs/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Swagger', resp.content.decode('utf-8') or '')
