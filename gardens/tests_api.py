from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token

from .models import GlobalNote
from .models import Garden

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

    def test_gardens_filtering_and_search(self):
        # create two users and gardens
        other = User.objects.create_user(username='other', password='pass')
        g1 = Garden.objects.create(owner=self.user, name='Alpha Garden', device_type='AHOPEGARDEN_12', is_public=True)
        g2 = Garden.objects.create(owner=other, name='Beta Garden', device_type='AHOPEGARDEN_12', is_public=False)

        # filter by owner username
        resp = self.client.get(f'/api/gardens/?owner__username={self.user.username}')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(any(item['name'] == 'Alpha Garden' for item in data.get('results', [])))

        # filter by is_public
        resp = self.client.get('/api/gardens/?is_public=true')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(all(item['is_public'] for item in data.get('results', [])))

        # search by name
        resp = self.client.get('/api/gardens/?search=Beta')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(any('Beta' in item['name'] for item in data.get('results', [])))

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
