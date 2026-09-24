from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token

from .models import Garden, GlobalNote, Pod

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
