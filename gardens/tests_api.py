from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token

from .models import DeveloperAccess, DeveloperAccessStatus, Garden, GlobalNote, Pod

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
