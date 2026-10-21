"""Tests for group-based access control (setup_groups command + mixin + nav)."""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from records.models import Appointment, Department, Doctor, MedicalNote, Patient

User = get_user_model()


def make_patient() -> Patient:
    return Patient.objects.create(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        date_of_birth=timezone.localdate() - timedelta(days=365 * 36),
    )


class SetupGroupsCommandTests(TestCase):
    def test_creates_both_groups_with_the_right_permissions(self):
        call_command("setup_groups")
        self.assertEqual(Group.objects.count(), 2)

        clinicians = set(
            Group.objects.get(name="Clinicians").permissions.values_list("codename", flat=True)
        )
        operations = set(
            Group.objects.get(name="Operations").permissions.values_list("codename", flat=True)
        )

        # Clinicians: full patient + appointment rights, no department rights.
        self.assertIn("add_patient", clinicians)
        self.assertIn("delete_patient", clinicians)
        self.assertIn("add_appointment", clinicians)
        self.assertIn("add_medicalnote", clinicians)
        self.assertNotIn("delete_department", clinicians)
        self.assertNotIn("add_doctor", clinicians)

        # Operations: full doctor + department rights, no patient writes.
        self.assertIn("add_doctor", operations)
        self.assertIn("delete_department", operations)
        self.assertIn("view_appointment", operations)
        self.assertNotIn("add_patient", operations)
        self.assertNotIn("add_appointment", operations)
        self.assertNotIn("change_patient", operations)

    def test_command_is_idempotent(self):
        call_command("setup_groups")
        call_command("setup_groups")
        self.assertEqual(Group.objects.count(), 2)

    def test_demo_users_flag_creates_one_user_per_group(self):
        call_command("setup_groups", "--demo-users")
        clinician = User.objects.get(username="clinician")
        self.assertEqual([g.name for g in clinician.groups.all()], ["Clinicians"])
        self.assertTrue(clinician.check_password("clin12345!"))
        self.assertFalse(clinician.is_staff)
        self.assertFalse(clinician.is_superuser)

        ops = User.objects.get(username="opsdesk")
        self.assertEqual([g.name for g in ops.groups.all()], ["Operations"])
        self.assertTrue(ops.check_password("ops12345!"))


class GroupAccessTests(TestCase):
    """Each group may open its own sections and is turned away from the others."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups")
        cls.clinician = User.objects.create_user("c1", password="x12345!!")
        cls.clinician.groups.add(Group.objects.get(name="Clinicians"))
        cls.operations = User.objects.create_user("o1", password="x12345!!")
        cls.operations.groups.add(Group.objects.get(name="Operations"))
        cls.groupless = User.objects.create_user("n1", password="x12345!!")
        cls.patient = make_patient()
        cls.department = Department.objects.create(name="Neurology", code="NEUR")
        cls.doctor = Doctor.objects.create(
            first_name="Gregory",
            last_name="House",
            email="house@riverside.example",
            specialty="neurology",
            license_number="LIC-TEST-1",
        )

    # -- anonymous --------------------------------------------------------
    def test_anonymous_visitor_is_sent_to_login(self):
        response = self.client.get(reverse("records:patient_list"))
        self.assertRedirects(response, "/accounts/login/?next=/patients/")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertRedirects(response, "/accounts/login/?next=/")

    # -- Clinicians -------------------------------------------------------
    def test_clinician_can_open_patient_section(self):
        self.client.force_login(self.clinician)
        self.assertEqual(self.client.get(reverse("records:patient_list")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("records:patient_detail", args=[self.patient.pk])).status_code,
            200,
        )

    def test_clinician_is_blocked_from_departments(self):
        self.client.force_login(self.clinician)
        response = self.client.get(reverse("records:department_list"), follow=True)
        self.assertContains(response, "does not have access")

    def test_clinician_cannot_create_or_delete_departments(self):
        self.client.force_login(self.clinician)
        response = self.client.post(reverse("records:department_create"), {
            "name": "Cardiology", "code": "CARD", "location": "Block C", "description": "",
        })
        self.assertEqual(Department.objects.count(), 1)  # only the fixture row
        self.assertRedirects(response, reverse("core:dashboard"))
        self.client.post(reverse("records:department_delete", args=[self.department.pk]))
        self.assertTrue(Department.objects.filter(pk=self.department.pk).exists())

    def test_clinician_can_view_but_not_manage_doctors(self):
        self.client.force_login(self.clinician)
        self.assertEqual(self.client.get(reverse("records:doctor_list")).status_code, 200)
        response = self.client.get(reverse("records:doctor_create"))
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_clinician_can_add_a_medical_note(self):
        self.client.force_login(self.clinician)
        self.client.post(reverse("core:add_note", args=[self.patient.pk]), {
            "note-title": "First visit",
            "note-body": "Patient feels much better today.",
            "note-doctor": "",
        })
        self.assertEqual(MedicalNote.objects.count(), 1)

    # -- Operations -------------------------------------------------------
    def test_operations_can_open_department_section(self):
        self.client.force_login(self.operations)
        self.assertEqual(self.client.get(reverse("records:department_list")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("records:department_detail", args=[self.department.pk])).status_code,
            200,
        )

    def test_operations_can_manage_doctors(self):
        self.client.force_login(self.operations)
        self.assertEqual(self.client.get(reverse("records:doctor_create")).status_code, 200)

    def test_operations_is_blocked_from_patients(self):
        self.client.force_login(self.operations)
        response = self.client.get(reverse("records:patient_list"), follow=True)
        self.assertContains(response, "does not have access")
        response = self.client.get(reverse("records:patient_detail", args=[self.patient.pk]))
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_operations_cannot_delete_a_patient(self):
        self.client.force_login(self.operations)
        self.client.post(reverse("records:patient_delete", args=[self.patient.pk]))
        self.assertTrue(Patient.objects.filter(pk=self.patient.pk).exists())

    def test_operations_can_view_but_not_book_appointments(self):
        self.client.force_login(self.operations)
        self.assertEqual(self.client.get(reverse("records:appointment_list")).status_code, 200)
        when = (timezone.now() + timedelta(days=2)).replace(second=0, microsecond=0)
        response = self.client.post(reverse("records:appointment_create"), {
            "patient": self.patient.pk,
            "doctor": self.doctor.pk,
            "scheduled_at": when.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_minutes": 30,
            "status": "scheduled",
            "reason": "Consultation about headaches",
            "notes": "",
        })
        self.assertRedirects(response, reverse("core:dashboard"))
        self.assertEqual(Appointment.objects.count(), 0)

    def test_operations_cannot_add_a_medical_note(self):
        self.client.force_login(self.operations)
        self.client.post(reverse("core:add_note", args=[self.patient.pk]), {
            "note-title": "Sneaky note",
            "note-body": "Trying to write clinical text here.",
            "note-doctor": "",
        })
        self.assertEqual(MedicalNote.objects.count(), 0)

    # -- no group / superuser --------------------------------------------
    def test_user_without_a_group_is_blocked_from_records(self):
        self.client.force_login(self.groupless)
        response = self.client.get(reverse("records:patient_list"), follow=True)
        self.assertContains(response, "does not have access")
        # ...but the dashboard still opens (with no clinical or ops panels).
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 200)

    def test_superuser_bypasses_every_group_check(self):
        User.objects.create_superuser("root", "root@x.example", "root12345!")
        self.client.force_login(User.objects.get(username="root"))
        self.assertEqual(self.client.get(reverse("records:patient_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("records:department_list")).status_code, 200)

    # -- dashboard & nav reflect the group --------------------------------
    def test_dashboard_panels_are_gated_by_group(self):
        self.client.force_login(self.clinician)
        response = self.client.get(reverse("core:dashboard"))
        self.assertContains(response, "Recently registered patients")
        self.assertContains(response, "Clinicians")  # group chip in the hero

        self.client.force_login(self.operations)
        response = self.client.get(reverse("core:dashboard"))
        self.assertNotContains(response, "Recently registered patients")
        self.assertContains(response, "Operations")
        self.assertNotContains(response, "/patients/")  # no patient stat/nav links

    def test_nav_links_follow_the_group(self):
        self.client.force_login(self.clinician)
        response = self.client.get(reverse("core:dashboard"))
        self.assertNotContains(response, 'href="/departments/"')

        self.client.force_login(self.operations)
        response = self.client.get(reverse("core:dashboard"))
        self.assertNotContains(response, 'href="/patients/"')
