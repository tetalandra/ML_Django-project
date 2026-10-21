"""Tests for the records app: models, inheritance, validation and CRUD."""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

import texttools

from .forms import AppointmentForm, MedicalNoteForm, PatientForm
from .models import Appointment, Department, Doctor, Inpatient, MedicalNote, Patient, PatientDirectory


def make_patient(**overrides) -> Patient:
    defaults = dict(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        date_of_birth=timezone.localdate() - timedelta(days=365 * 36),
        gender="f",
        blood_group="O+",
    )
    defaults.update(overrides)
    return Patient.objects.create(**defaults)


def make_doctor(**overrides) -> Doctor:
    defaults = dict(
        first_name="Gregory",
        last_name="House",
        email="house@riverside.example",
        specialty="neurology",
        license_number="LIC-TEST-1",
    )
    defaults.update(overrides)
    return Doctor.objects.create(**defaults)


class PersonModelTests(TestCase):
    def test_full_name_and_str(self):
        patient = make_patient()
        self.assertEqual(patient.full_name, "Ada Lovelace")
        self.assertEqual(str(patient), "Ada Lovelace")

    def test_age_is_calculated(self):
        patient = make_patient(date_of_birth=timezone.localdate().replace(year=2000))
        self.assertEqual(patient.age, timezone.localdate().year - 2000)

    def test_rejects_future_date_of_birth(self):
        patient = Patient(
            first_name="Baby",
            last_name="Test",
            email="baby@example.com",
            date_of_birth=timezone.localdate() + timedelta(days=5),
        )
        with self.assertRaises(Exception):
            patient.full_clean()


class InheritanceTests(TestCase):
    """The three flavours of Django inheritance used in this project."""

    def test_multi_table_inpatient_is_also_a_patient(self):
        inpatient = Inpatient.objects.create(
            first_name="Jack",
            last_name="Jones",
            email="jack@example.com",
            date_of_birth=timezone.localdate() - timedelta(days=365 * 50),
            ward="Blue",
            room_number="301",
            daily_rate=200,
        )
        # Same row reachable through the parent table...
        self.assertTrue(Patient.objects.filter(pk=inpatient.pk).exists())
        # ...and the child link works both directions.
        self.assertEqual(inpatient.patient_ptr_id, inpatient.pk)
        self.assertEqual(inpatient.ward, "Blue")

    def test_length_of_stay_and_bill(self):
        admitted = timezone.localdate() - timedelta(days=3)
        inpatient = Inpatient.objects.create(
            first_name="Jill",
            last_name="Jones",
            email="jill@example.com",
            date_of_birth=timezone.localdate() - timedelta(days=365 * 40),
            admitted_on=admitted,
            daily_rate=100,
        )
        self.assertEqual(inpatient.length_of_stay, 3)
        self.assertEqual(inpatient.estimated_bill, 300.0)
        self.assertTrue(inpatient.is_currently_admitted)

    def test_inpatient_discharge_before_admission_is_invalid(self):
        inpatient = Inpatient(
            first_name="Bad",
            last_name="Dates",
            email="bad@example.com",
            date_of_birth=timezone.localdate() - timedelta(days=365 * 30),
            admitted_on=timezone.localdate(),
            discharged_on=timezone.localdate() - timedelta(days=1),
        )
        with self.assertRaises(Exception):
            inpatient.full_clean()

    def test_proxy_model_uses_same_table_but_own_ordering(self):
        make_patient(first_name="Zoe", last_name="Alpha", email="zoe@example.com")
        make_patient(first_name="Adam", last_name="Zulu", email="adam@example.com")
        names = [p.first_name for p in PatientDirectory.objects.all()]
        self.assertEqual(names, ["Adam", "Zoe"])  # proxy orders by first name
        parent_names = [p.first_name for p in Patient.objects.all()]
        self.assertEqual(parent_names, ["Zoe", "Adam"])  # parent orders by last name
        # The proxy query still yields Patient instances (same table, same rows).
        self.assertTrue(all(isinstance(p, Patient) for p in PatientDirectory.objects.all()))


class AppointmentTests(TestCase):
    def setUp(self):
        self.patient = make_patient()
        self.doctor = make_doctor()

    def test_is_upcoming_property(self):
        future = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_at=timezone.now() + timedelta(days=1),
            reason="Checkup",
        )
        past = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_at=timezone.now() - timedelta(days=1),
            reason="Old visit",
        )
        self.assertTrue(future.is_upcoming)
        self.assertFalse(past.is_upcoming)

    def test_form_rejects_double_booking(self):
        when = timezone.now().replace(microsecond=0)
        Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, scheduled_at=when, reason="First"
        )
        form = AppointmentForm(data={
            "patient": self.patient.pk,
            "doctor": self.doctor.pk,
            "scheduled_at": when.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_minutes": 30,
            "status": "scheduled",
            "reason": "Clashing visit",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("doctor already has this patient booked", str(form.errors))


class MedicalNoteTextToolsTests(TestCase):
    """Our own package powers the clinical note statistics."""

    def setUp(self):
        self.patient = make_patient()
        self.note = MedicalNote.objects.create(
            patient=self.patient,
            title="Racecar",
            body="level up with racecar fun",
        )

    def test_word_and_character_counts_come_from_texttools(self):
        self.assertEqual(self.note.word_count, texttools.count_words("level up with racecar fun"))
        self.assertEqual(self.note.word_count, 5)
        self.assertEqual(self.note.character_count, texttools.count_characters("level up with racecar fun"))

    def test_summary_is_title_cased_and_truncated(self):
        self.assertTrue(self.note.summary.startswith("Level Up"))

    def test_palindrome_title_detection(self):
        self.assertTrue(self.note.title_is_palindrome)


class WordLimitTests(TestCase):
    """texttools word limits are enforced through the ordinary forms."""

    def setUp(self):
        self.patient = make_patient()
        self.doctor = make_doctor()

    def appointment_data(self, **overrides):
        data = {
            "patient": self.patient.pk,
            "doctor": self.doctor.pk,
            "scheduled_at": "2030-01-15 10:00:00",
            "duration_minutes": 30,
            "status": "scheduled",
            "reason": "Annual checkup",
            "notes": "",
        }
        data.update(overrides)
        return data

    def patient_data(self, **overrides):
        data = {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "phone": "+1 555 0001",
            "address": "",
            "date_of_birth": "1990-01-01",
            "gender": "f",
            "blood_group": "O+",
            "allergies": "",
            "medical_history": "None",
        }
        data.update(overrides)
        return data

    def test_appointment_reason_rejects_more_than_15_words(self):
        form = AppointmentForm(data=self.appointment_data(reason=" ".join(["word"] * 16)))
        self.assertFalse(form.is_valid())
        self.assertIn("texttools counted 16", str(form.errors["reason"]))

    def test_appointment_reason_accepts_exactly_15_words(self):
        form = AppointmentForm(data=self.appointment_data(reason=" ".join(["word"] * 15)))
        self.assertTrue(form.is_valid(), form.errors)

    def test_medical_history_rejects_more_than_50_words(self):
        form = PatientForm(data=self.patient_data(medical_history=" ".join(["word"] * 51)))
        self.assertFalse(form.is_valid())
        self.assertIn("texttools counted 51", str(form.errors["medical_history"]))

    def test_note_body_rejects_more_than_120_words(self):
        form = MedicalNoteForm(data={
            "title": "Long note",
            "body": " ".join(["word"] * 121),
            "doctor": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("texttools counted 121", str(form.errors["body"]))

    def test_note_body_rejects_fewer_than_3_words(self):
        form = MedicalNoteForm(data={"title": "Short", "body": "Too short.", "doctor": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("at least 3 words", str(form.errors["body"]))

    def test_widget_carries_limit_for_live_counter(self):
        """The browser counter reads data-word-limit straight off the widget."""
        form = AppointmentForm()
        self.assertEqual(form.fields["reason"].widget.attrs["data-word-limit"], 15)


class CrudViewTests(TestCase):
    def setUp(self):
        # Pages now require login; a superuser passes every group check.
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_superuser(
            "root", "root@x.example", "root12345!"
        )
        self.client.force_login(user)

    def test_dashboard_renders(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")

    def test_patient_list_and_search(self):
        make_patient()
        make_patient(first_name="Nikola", last_name="Tesla", email="nikola@example.com")
        response = self.client.get(reverse("records:patient_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Lovelace")

        response = self.client.get(reverse("records:patient_list"), {"q": "tesla"})
        self.assertContains(response, "Nikola Tesla")
        self.assertNotContains(response, "Ada Lovelace")

    def test_patient_create_update_delete_cycle(self):
        form_data = {
            "first_name": "Marie",
            "last_name": "Curie",
            "email": "marie@example.com",
            "phone": "+1 555 0001",
            "address": "Lab Street 1",
            "date_of_birth": "1967-11-07",
            "gender": "f",
            "blood_group": "A+",
            "allergies": "",
            "medical_history": "",
        }
        # Create
        response = self.client.post(reverse("records:patient_create"), form_data)
        patient = Patient.objects.get(email="marie@example.com")
        self.assertRedirects(response, patient.get_absolute_url())

        # Read
        response = self.client.get(patient.get_absolute_url())
        self.assertContains(response, "Marie Curie")

        # Update
        updated = dict(form_data, last_name="Curie-Kelvin")
        response = self.client.post(
            reverse("records:patient_update", args=[patient.pk]), updated
        )
        patient.refresh_from_db()
        self.assertEqual(patient.last_name, "Curie-Kelvin")
        self.assertRedirects(response, patient.get_absolute_url())

        # Delete
        response = self.client.post(reverse("records:patient_delete", args=[patient.pk]))
        self.assertRedirects(response, reverse("records:patient_list"))
        self.assertFalse(Patient.objects.filter(pk=patient.pk).exists())

    def test_doctor_create_requires_valid_form(self):
        response = self.client.post(reverse("records:doctor_create"), {
            "first_name": "No",
            "last_name": "License",
            "email": "not-an-email",
            "phone": "",
            "address": "",
            "specialty": "surgery",
            "license_number": "",
            "department": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "email", "Enter a valid email address.")
        self.assertEqual(Doctor.objects.count(), 0)

    def test_department_crud(self):
        response = self.client.post(reverse("records:department_create"), {
            "name": "Neurology", "code": "neur", "location": "Block D", "description": "Brain care.",
        })
        department = Department.objects.get(name="Neurology")
        self.assertEqual(department.code, "NEUR")  # cleaned to uppercase
        self.assertRedirects(response, department.get_absolute_url())
        self.assertContains(
            self.client.get(reverse("records:department_list")), "Neurology"
        )
        self.client.post(reverse("records:department_delete", args=[department.pk]))
        self.assertEqual(Department.objects.count(), 0)

    def test_appointment_booking_through_view(self):
        patient = make_patient()
        doctor = make_doctor()
        when = (timezone.now() + timedelta(days=2)).replace(second=0, microsecond=0)
        response = self.client.post(reverse("records:appointment_create"), {
            "patient": patient.pk,
            "doctor": doctor.pk,
            "scheduled_at": when.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_minutes": 30,
            "status": "scheduled",
            "reason": "Consultation about headaches",
            "notes": "",
        })
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertRedirects(response, Appointment.objects.get().get_absolute_url())

    def test_404_for_missing_detail(self):
        response = self.client.get(reverse("records:patient_detail", args=[999]))
        self.assertEqual(response.status_code, 404)
