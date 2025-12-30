from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token

from .models import GlobalNote

User = get_user_model()


class ApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='apiuser', password='pass')
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
