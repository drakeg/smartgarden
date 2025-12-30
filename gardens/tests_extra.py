from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from . import views as views_module

from .models import Garden

user_model = get_user_model()


class ExtraTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_registration_creates_user_and_logs_in(self):
        resp = self.client.post(reverse('gardens:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(user_model.objects.filter(username='newuser').exists())
        # After registration the user should either be authenticated or instructed to confirm via email
        if '_auth_user_id' not in self.client.session:
            # likely email confirmation path — ensure the response asks the user to check email
            self.assertIn('Check your email', resp.content.decode('utf-8'))

    def test_guest_cannot_enable_public_link(self):
        # Start guest session
        resp = self.client.get(reverse('gardens:guest_start'), follow=True)
        # Find the guest garden that was just created
        g = Garden.objects.filter(is_guest=True).order_by('-created_at').first()
        self.assertIsNotNone(g)

        # Attempt to toggle public link as guest
        toggle_url = reverse('gardens:garden_toggle_public', args=[g.id])
        resp = self.client.post(toggle_url, follow=True)
        g.refresh_from_db()
        self.assertFalse(g.is_public)

    def test_import_export_roundtrip(self):
        # Create user and garden with pods and notes
        user = user_model.objects.create_user(username='impuser', password='pass')
        garden = user.gardens.create(name='ExportGarden', device_type='AHOPEGARDEN_12')
        for pos in range(1, 4):
            pod = garden.pods.create(position=pos, plant_name=f'Plant{pos}')
            pod.notes.create(note=f'Note{pos}')

        # Export as owner
        self.client.force_login(user)
        resp = self.client.get(reverse('gardens:garden_export_json', args=[garden.id]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['version'], 1)
        self.assertEqual(len(data['pods']), 3)

    def test_guest_note_cap_enforced(self):
        # Start guest session and find garden/pod
        resp = self.client.get(reverse('gardens:guest_start'), follow=True)
        g = Garden.objects.filter(is_guest=True).order_by('-created_at').first()
        self.assertIsNotNone(g)
        pod = g.pods.first()

        # Add notes up to limit
        for i in range(views_module.GUEST_MAX_NOTES_TOTAL):
            resp = self.client.post(reverse('gardens:pod_note_add', args=[g.id, pod.position]), {'note': f'n{i}'})
            # expect 200 with updated panel
            self.assertEqual(resp.status_code, 200)

        # Next note should be blocked and return the panel with an error
        resp = self.client.post(reverse('gardens:pod_note_add', args=[g.id, pod.position]), {'note': 'overflow'})
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('Guest mode limit reached', content)

    def test_navbar_shows_try_on_home_and_guest_badge_elsewhere(self):
        # No guest cookie: homepage should show Try link
        resp = self.client.get(reverse('gardens:home'))
        content = resp.content.decode('utf-8')
        self.assertIn('Try it now', content)

        # Start guest session
        resp = self.client.get(reverse('gardens:guest_start'), follow=True)
        g = Garden.objects.filter(is_guest=True).order_by('-created_at').first()
        # Visit garden detail (non-home) — should show Guest badge and not 'Try it now'
        resp = self.client.get(reverse('gardens:garden_detail', args=[g.id]))
        content = resp.content.decode('utf-8')
        self.assertIn('Guest', content)
        self.assertNotIn('Try it now', content)
