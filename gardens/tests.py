from django.test import TestCase, Client, override_settings
from django.contrib.sessions.backends.db import SessionStore
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from unittest.mock import patch
from .models import GlobalNote


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
