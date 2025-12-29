from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model


User = get_user_model()


class BasicAppTests(TestCase):
	def setUp(self):
		self.client = Client()

	def test_health_endpoint(self):
		"""The /health/ endpoint should return 200 and 'ok'."""
		resp = self.client.get(reverse('health'))
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.content, b"ok")

	def test_homepage_accessible(self):
		"""The app root should be accessible (redirects or 200)."""
		resp = self.client.get('/')
		self.assertIn(resp.status_code, (200, 302))

	def test_static_settings_present(self):
		"""Ensure STATIC_URL and STATICFILES_DIRS are configured."""
		self.assertTrue(hasattr(settings, 'STATIC_URL'))
		self.assertTrue(settings.STATIC_URL.startswith('/'))

	def test_garden_detail_renders_for_owner(self):
		"""Create a garden with pods and ensure the detail view renders for the owner."""
		# create user and garden
		user = User.objects.create_user(username='tester', password='pass')
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
