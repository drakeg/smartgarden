from django.test import TestCase, Client, override_settings
from django.contrib.sessions.backends.db import SessionStore
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.core.cache import caches
from unittest.mock import patch
from rest_framework.authtoken.models import Token
from .models import DeveloperAccess, DeveloperAccessStatus, DeveloperApiUsageDaily, DeveloperPlan, GlobalNote


user_model = get_user_model()


class BasicAppTests(TestCase):
	def setUp(self):
		self.client = Client()

	def test_health_endpoint(self):
		"""The /health/ endpoint should return 200 and 'ok'."""
		resp = self.client.get(reverse('health'))
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.content, b"ok")

	def test_readiness_endpoint_reports_database_ready(self):
		"""The readiness endpoint should verify the database and return 200."""
		resp = self.client.get(reverse('readiness'))
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.content, b"ready")

	def test_readiness_endpoint_returns_503_when_database_is_unavailable(self):
		"""Database failures should make the app not ready without changing liveness."""
		with patch('smartgarden.views.connection.cursor', side_effect=DatabaseError('offline')):
			resp = self.client.get(reverse('readiness'))

		self.assertEqual(resp.status_code, 503)
		self.assertEqual(resp.content, b"database unavailable")

		health = self.client.get(reverse('health'))
		self.assertEqual(health.status_code, 200)
		self.assertEqual(health.content, b"ok")

	@override_settings(
		SECURE_SSL_REDIRECT=True,
		SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
	)
	def test_trusted_forwarded_https_avoids_redirect_loop(self):
		resp = self.client.get('/health/', HTTP_X_FORWARDED_PROTO='https')
		self.assertEqual(resp.status_code, 200)

	@override_settings(
		SECURE_SSL_REDIRECT=True,
		SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
	)
	def test_untrusted_http_request_still_redirects_to_https(self):
		resp = self.client.get('/health/')
		self.assertEqual(resp.status_code, 301)
		self.assertTrue(resp['Location'].startswith('https://'))

	def test_homepage_accessible(self):
		"""The app root should be accessible (redirects or 200)."""
		resp = self.client.get('/')
		self.assertIn(resp.status_code, (200, 302))

	def test_static_settings_present(self):
		"""Ensure STATIC_URL and STATICFILES_DIRS are configured."""
		self.assertTrue(hasattr(settings, 'STATIC_URL'))
		self.assertTrue(settings.STATIC_URL.startswith('/'))

	def test_email_settings_are_configured(self):
		"""Email settings should be explicit instead of relying on Django defaults."""
		self.assertTrue(hasattr(settings, 'EMAIL_BACKEND'))
		self.assertTrue(hasattr(settings, 'DEFAULT_FROM_EMAIL'))
		self.assertTrue(hasattr(settings, 'EMAIL_HOST'))
		self.assertTrue(hasattr(settings, 'EMAIL_PORT'))
		self.assertTrue(hasattr(settings, 'EMAIL_TIMEOUT'))

	def test_database_session_roundtrip_uses_configured_secret_key(self):
		"""Database-backed session payloads should decode with the configured key."""
		session = SessionStore()
		session['probe'] = 'smartgarden'
		session.save()

		reloaded = SessionStore(session_key=session.session_key)
		self.assertEqual(reloaded.get('probe'), 'smartgarden')

	def test_garden_detail_renders_for_owner(self):
		"""Create a garden with pods and ensure the detail view renders for the owner."""
		# create user and garden
		user = user_model.objects.create_user(username='tester', password='pass')
		garden = user.gardens.create(name='My Test Garden')

		# create a few pods
		for pos in range(1, 4):
			garden.pods.create(position=pos)

		# login and fetch detail
		self.client.force_login(user)
		url = reverse('gardens:garden_detail', args=[garden.id])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)

		# check that pod positions are rendered
		content = resp.content.decode('utf-8')
		self.assertIn('Pod 1', content)
		self.assertIn('Pod 2', content)
		self.assertIn('Pod 3', content)

	def test_global_note_model(self):
		"""Ensure a GlobalNote can be created and queried."""
		user = user_model.objects.create_user(username='notes', password='pass')
		note = user.global_notes.create(title='Test tip', note='This plant fails in shade')
		self.assertIn('Test tip', str(note))
		self.assertEqual(GlobalNote.objects.count(), 1)


class DeveloperDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = user_model.objects.create_user(
            username='developer',
            password='developer-pass',
        )

    def test_dashboard_requires_authentication(self):
        resp = self.client.get(reverse('gardens:developer_dashboard'))

        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('gardens:login'), resp['Location'])

    @override_settings(
        API_PAYWALL_ENABLED=True,
        API_PLAN_THROTTLE_RATES={
            'STARTER': '10/minute',
            'PRO': '20/minute',
            'ENTERPRISE': '30/minute',
        },
    )
    def test_dashboard_renders_access_quota_usage_and_never_existing_token_value(self):
        access = DeveloperAccess.objects.create(
            user=self.user,
            plan=DeveloperPlan.PRO,
            status=DeveloperAccessStatus.ACTIVE,
        )
        token = Token.objects.create(user=self.user)
        DeveloperApiUsageDaily.objects.create(
            user=self.user,
            usage_date=timezone.localdate(),
            plan=DeveloperPlan.PRO,
            request_count=7,
            success_count=6,
            client_error_count=1,
        )
        caches['developer_api'].clear()
        self.client.force_login(self.user)

        resp = self.client.get(reverse('gardens:developer_dashboard'))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Developer Dashboard')
        self.assertContains(resp, access.get_plan_display())
        self.assertContains(resp, '20/minute')
        self.assertContains(resp, '7')
        self.assertContains(resp, 'Export 30-day CSV')
        self.assertNotContains(resp, token.key)

    def test_dashboard_wrong_password_does_not_rotate_token(self):
        token = Token.objects.create(user=self.user)
        old_key = token.key
        self.client.force_login(self.user)

        resp = self.client.post(
            reverse('gardens:developer_dashboard'),
            {'action': 'rotate_token', 'password': 'wrong-password'},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Password confirmation failed.')
        self.assertTrue(Token.objects.filter(user=self.user, key=old_key).exists())
        self.assertNotContains(resp, old_key)

    def test_dashboard_rotation_invalidates_old_token_and_shows_new_token_once(self):
        token = Token.objects.create(user=self.user)
        old_key = token.key
        self.client.force_login(self.user)

        resp = self.client.post(
            reverse('gardens:developer_dashboard'),
            {'action': 'rotate_token', 'password': 'developer-pass'},
        )

        self.assertEqual(resp.status_code, 200)
        new_token = Token.objects.get(user=self.user)
        self.assertNotEqual(new_token.key, old_key)
        self.assertFalse(Token.objects.filter(key=old_key).exists())
        self.assertContains(resp, new_token.key)
        self.assertNotContains(resp, old_key)

        followup = self.client.get(reverse('gardens:developer_dashboard'))
        self.assertEqual(followup.status_code, 200)
        self.assertNotContains(followup, new_token.key)

    def test_dashboard_can_issue_first_token_with_password_confirmation(self):
        self.client.force_login(self.user)

        resp = self.client.post(
            reverse('gardens:developer_dashboard'),
            {'action': 'rotate_token', 'password': 'developer-pass'},
        )

        self.assertEqual(resp.status_code, 200)
        token = Token.objects.get(user=self.user)
        self.assertContains(resp, token.key)

    def test_dashboard_revocation_requires_password_and_removes_token(self):
        token = Token.objects.create(user=self.user)
        old_key = token.key
        self.client.force_login(self.user)

        denied = self.client.post(
            reverse('gardens:developer_dashboard'),
            {'action': 'revoke_token', 'password': 'wrong-password'},
        )
        self.assertEqual(denied.status_code, 200)
        self.assertTrue(Token.objects.filter(key=old_key).exists())

        revoked = self.client.post(
            reverse('gardens:developer_dashboard'),
            {'action': 'revoke_token', 'password': 'developer-pass'},
        )
        self.assertEqual(revoked.status_code, 200)
        self.assertContains(revoked, 'API token revoked.')
        self.assertFalse(Token.objects.filter(user=self.user).exists())
        self.assertNotContains(revoked, old_key)
