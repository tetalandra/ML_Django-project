"""Tests for the core app: dashboard and texttools template filters."""

from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from core.templatetags.texttools_extras import char_count, snippet, smart_title, word_count
from records.models import MedicalNote, Patient
from datetime import timedelta

from django.utils import timezone


class DashboardTests(TestCase):
    def setUp(self):
        # The dashboard now requires login (group access control);
        # a superuser sees every panel regardless of group.
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_superuser(
            "root", "root@x.example", "root12345!"
        )
        self.client.force_login(user)

    def test_dashboard_renders_with_empty_database(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Insights")
        self.assertContains(response, "texttools")

    def test_dashboard_counts_patients(self):
        Patient.objects.create(
            first_name="Solo", last_name="Dolo", email="solo@example.com",
            date_of_birth=timezone.localdate() - timedelta(days=365 * 30),
        )
        response = self.client.get(reverse("core:dashboard"))
        self.assertContains(response, 'class="stat-n">1<')


class MedicalNoteViewTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_superuser(
            "root", "root@x.example", "root12345!"
        )
        self.client.force_login(user)
        self.patient = Patient.objects.create(
            first_name="Note", last_name="Taker", email="note@example.com",
            date_of_birth=timezone.localdate() - timedelta(days=365 * 25),
        )

    def test_adding_note_from_patient_page(self):
        response = self.client.post(
            reverse("core:add_note", args=[self.patient.pk]),
            {"note-title": "First visit", "note-body": "Patient feels much better today.", "note-doctor": ""},
        )
        self.assertRedirects(response, self.patient.get_absolute_url())
        note = MedicalNote.objects.get()
        self.assertEqual(note.patient, self.patient)
        self.assertEqual(note.word_count, 5)

    def test_short_note_is_rejected(self):
        response = self.client.post(
            reverse("core:add_note", args=[self.patient.pk]),
            {"note-title": "Too short", "note-body": "No.", "note-doctor": ""},
            follow=True,
        )
        self.assertEqual(MedicalNote.objects.count(), 0)
        self.assertContains(response, "at least 3 words")


class AdminRedirectTests(TestCase):
    """Login/logout must never land on the stock /accounts/profile/ 404."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_superuser("admin", "admin@x.example", "pw12345!!")

    def test_login_without_next_goes_to_dashboard(self):
        response = self.client.post("/admin/login/", {
            "username": "admin", "password": "pw12345!!",
        })
        self.assertRedirects(response, "/")

    def test_login_with_next_honors_it(self):
        response = self.client.post("/admin/login/", {
            "username": "admin", "password": "pw12345!!", "next": "/admin/",
        })
        self.assertRedirects(response, "/admin/")

    def test_logout_goes_to_dashboard(self):
        self.client.post("/admin/login/", {"username": "admin", "password": "pw12345!!"})
        response = self.client.post("/admin/logout/")
        # Logout still targets "/", but as an anonymous visitor the dashboard
        # now redirects onward to the login page, so don't follow it.
        self.assertRedirects(response, "/", fetch_redirect_response=False)


class TemplateFilterTests(TestCase):
    def test_word_and_char_count(self):
        self.assertEqual(word_count("one two three"), 3)
        self.assertEqual(char_count("abc de"), 6)

    def test_smart_title_and_snippet(self):
        self.assertEqual(smart_title("hello world"), "Hello World")
        self.assertEqual(snippet("a very long sentence here", 10), "a very ...")

    def test_snippet_handles_short_text(self):
        self.assertEqual(snippet("short", 50), "short")
