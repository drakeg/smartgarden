import json
from unittest.mock import patch

from django.core import mail, signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
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

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='noreply@example.com',
    )
    def test_registration_email_has_plain_text_and_html_parts(self):
        resp = self.client.post(reverse('gardens:register'), {
            'username': 'emailuser',
            'email': 'emailuser@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
        })
        self.assertEqual(resp.status_code, 200)

        user = user_model.objects.get(username='emailuser')
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Confirm your Smart Garden account')
        self.assertEqual(message.to, ['emailuser@example.com'])
        self.assertIn('Please confirm your Smart Garden account', message.body)
        self.assertEqual(len(message.alternatives), 1)
        self.assertEqual(message.alternatives[0].mimetype, 'text/html')
        self.assertIn('Confirm your account', message.alternatives[0].content)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='noreply@example.com',
    )
    def test_confirmation_sends_multipart_welcome_email(self):
        user = user_model.objects.create_user(
            username='welcomeuser',
            email='welcome@example.com',
            password='complexpass123',
            is_active=False,
        )
        token = signing.dumps({'user_id': user.pk}, salt='email-confirm')

        resp = self.client.get(reverse('gardens:confirm_registration', args=[token]))
        self.assertEqual(resp.status_code, 200)

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Welcome to Smart Garden')
        self.assertIn('Your Smart Garden account is confirmed', message.body)
        self.assertEqual(len(message.alternatives), 1)
        self.assertEqual(message.alternatives[0].mimetype, 'text/html')
        self.assertIn('welcome!', message.alternatives[0].content.lower())

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='noreply@example.com',
        CELERY_BROKER_URL='',
    )
    def test_registration_email_falls_back_to_synchronous_send_without_broker(self):
        self.client.post(reverse('gardens:register'), {
            'username': 'syncuser',
            'email': 'sync@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
        })
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['sync@example.com'])

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='noreply@example.com',
        CELERY_BROKER_URL='memory://',
    )
    @patch('gardens.tasks.send_templated_email_task.delay')
    def test_registration_email_is_queued_when_broker_is_configured(self, delay_mock):
        resp = self.client.post(reverse('gardens:register'), {
            'username': 'asyncuser',
            'email': 'async@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        delay_mock.assert_called_once()
        args = delay_mock.call_args.args
        self.assertEqual(args[0], 'Confirm your Smart Garden account')
        self.assertEqual(args[1], 'async@example.com')
        self.assertEqual(args[2], 'confirm_registration')
        self.assertEqual(args[3]['username'], 'asyncuser')
        self.assertIn('/accounts/confirm/', args[3]['confirm_url'])

    def test_guest_start_sets_cookie_and_reuses_same_garden(self):
        resp = self.client.get(reverse('gardens:guest_start'))
        self.assertEqual(resp.status_code, 302)

        g = Garden.objects.get(is_guest=True)
        self.assertIn(views_module.GUEST_COOKIE_NAME, self.client.cookies)
        cookie = self.client.cookies[views_module.GUEST_COOKIE_NAME]
        self.assertEqual(cookie.value, g.guest_token)
        self.assertEqual(cookie['httponly'], True)
        self.assertEqual(cookie['samesite'], 'Lax')

        second = self.client.get(reverse('gardens:guest_start'))
        self.assertEqual(second.status_code, 302)
        self.assertEqual(Garden.objects.filter(is_guest=True).count(), 1)
        self.assertEqual(second.url, reverse('gardens:garden_detail', args=[g.id]))

    def test_guest_cannot_enable_public_link(self):
        self.client.get(reverse('gardens:guest_start'), follow=True)
        g = Garden.objects.filter(is_guest=True).order_by('-created_at').first()
        self.assertIsNotNone(g)

        toggle_url = reverse('gardens:garden_toggle_public', args=[g.id])
        self.client.post(toggle_url, follow=True)
        g.refresh_from_db()
        self.assertFalse(g.is_public)

    def test_import_export_roundtrip(self):
        user = user_model.objects.create_user(username='impuser', password='pass')
        garden = user.gardens.create(name='ExportGarden', device_type='AHOPEGARDEN_12')
        for pos in range(1, 4):
            pod = garden.pods.create(position=pos, plant_name=f'Plant{pos}')
            pod.notes.create(note=f'Note{pos}')

        self.client.force_login(user)
        export_resp = self.client.get(reverse('gardens:garden_export_json', args=[garden.id]))
        self.assertEqual(export_resp.status_code, 200)
        data = export_resp.json()
        self.assertEqual(data['version'], 1)
        self.assertEqual(len(data['pods']), 3)

        upload = SimpleUploadedFile(
            'garden.json',
            json.dumps(data).encode('utf-8'),
            content_type='application/json',
        )
        import_resp = self.client.post(
            reverse('gardens:garden_import_json'),
            {'import_file': upload},
            follow=True,
        )
        self.assertEqual(import_resp.status_code, 200)

        imported = user.gardens.exclude(id=garden.id).get()
        self.assertEqual(imported.name, 'ExportGarden')
        self.assertEqual(imported.device_type, 'AHOPEGARDEN_12')
        self.assertEqual(imported.pods.count(), 12)

        for pos in range(1, 4):
            pod = imported.pods.get(position=pos)
            self.assertEqual(pod.plant_name, f'Plant{pos}')
            self.assertEqual(list(pod.notes.values_list('note', flat=True)), [f'Note{pos}'])

    def test_import_missing_optional_fields_uses_defaults(self):
        user = user_model.objects.create_user(username='defaultsuser', password='pass')
        self.client.force_login(user)
        payload = {
            'version': views_module.EXPORT_VERSION,
            'pods': [
                {'position': 1},
                {'position': 2, 'plant_name': 'Basil'},
                {'position': 'not-a-number', 'plant_name': 'Ignored'},
            ],
        }
        upload = SimpleUploadedFile(
            'minimal.json',
            json.dumps(payload).encode('utf-8'),
            content_type='application/json',
        )

        resp = self.client.post(
            reverse('gardens:garden_import_json'),
            {'import_file': upload},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)

        imported = user.gardens.get()
        self.assertEqual(imported.name, 'Imported Garden')
        self.assertEqual(imported.device_type, 'GENERIC_12')
        self.assertEqual(imported.pods.count(), 12)
        self.assertEqual(imported.pods.get(position=1).plant_name, '')
        self.assertEqual(imported.pods.get(position=2).plant_name, 'Basil')

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
