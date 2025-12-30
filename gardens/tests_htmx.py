from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase, Client

from .models import GlobalNote

user_model = get_user_model()


class HtmxNotesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = user_model.objects.create_user(username='htmx', password='pass')

    def test_htmx_create_note(self):
        self.client.force_login(self.user)
        resp = self.client.post('/gardens/notes/create/', {'title': 'HX', 'note': 'via htmx'}, HTTP_HX_REQUEST='true')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(GlobalNote.objects.count(), 1)
        self.assertIn('HX', resp.content.decode('utf-8'))

    def test_htmx_delete_note(self):
        self.client.force_login(self.user)
        note = GlobalNote.objects.create(author=self.user, title='Del', note='to delete')
        resp = self.client.post(f'/gardens/notes/{note.id}/delete/', HTTP_HX_REQUEST='true')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(GlobalNote.objects.count(), 0)

    def test_htmx_edit_note_flow(self):
        self.client.force_login(self.user)
        note = GlobalNote.objects.create(author=self.user, title='Old', note='old')
        # GET edit form via HTMX
        resp = self.client.get(f'/gardens/notes/{note.id}/edit/', HTTP_HX_REQUEST='true')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Save', resp.content.decode('utf-8'))
        # POST updated data via HTMX
        resp = self.client.post(f'/gardens/notes/{note.id}/edit/', {'title': 'New', 'note': 'updated'}, HTTP_HX_REQUEST='true')
        self.assertEqual(resp.status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.title, 'New')
