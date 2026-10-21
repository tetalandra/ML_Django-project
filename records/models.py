"""Hospital records models.

Demonstrations of inheritance in Django:

* ``TimeStampedModel`` / ``Person`` — **abstract** base models (code reuse, no table)
* ``Inpatient``                     — **multi-table** inheritance (own table + implicit OneToOne to Patient)
* ``PatientDirectory``              — **proxy** model (same table, custom default ordering)
* ``Doctor(Person, TimeStampedModel)`` — combining two abstract bases

And plenty of relationships between real tables: Department, Doctor,
Patient, Inpatient, Appointment and MedicalNote.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

import texttools

from .validators import max_words, min_words


class TimeStampedModel(models.Model):
    """Abstract base that keeps ``created_at`` / ``updated_at`` on every row."""

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class Person(models.Model):
    """Abstract base for anybody with a name and contact details."""

    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=25,
        blank=True,
        validators=[RegexValidator(r"^[\d+\-\s()]{7,25}$", "Enter a valid phone number.")],
    )
    address = models.CharField(max_length=200, blank=True)

    class Meta:
        abstract = True
        ordering = ("last_name", "first_name")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.full_name


class Department(TimeStampedModel):
    """A hospital department that doctors can belong to."""

    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=10, unique=True, help_text="Short code, e.g. CARD.")
    location = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True, validators=[max_words(40)],
                                   help_text="What this department does (up to 40 words).")

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "departments"

    def get_absolute_url(self) -> str:
        return reverse("records:department_detail", args=[self.pk])

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Doctor(Person, TimeStampedModel):
    """A doctor: inherits person fields from ``Person`` and timestamps too."""

    SPECIALTIES = [
        ("cardiology", "Cardiology"),
        ("dermatology", "Dermatology"),
        ("emergency", "Emergency"),
        ("neurology", "Neurology"),
        ("oncology", "Oncology"),
        ("pediatrics", "Pediatrics"),
        ("radiology", "Radiology"),
        ("surgery", "Surgery"),
    ]

    specialty = models.CharField(max_length=40, choices=SPECIALTIES, default="general")
    license_number = models.CharField(max_length=40, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doctors",
    )

    class Meta(Person.Meta):
        pass

    def get_absolute_url(self) -> str:
        return reverse("records:doctor_detail", args=[self.pk])

    @property
    def specialty_label(self) -> str:
        return self.get_specialty_display()


class Patient(Person, TimeStampedModel):
    """A patient: shares the person table layout through the abstract base."""

    GENDERS = [("f", "Female"), ("m", "Male"), ("other", "Other")]
    BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

    date_of_birth = models.DateField()
    gender = models.CharField(max_length=6, choices=GENDERS, default="other")
    blood_group = models.CharField(max_length=3, blank=True, choices=[(b, b) for b in BLOOD_GROUPS])
    allergies = models.CharField(max_length=200, blank=True, help_text="Comma separated, e.g. penicillin, pollen")
    medical_history = models.TextField(
        blank=True,
        validators=[max_words(50)],
        help_text="Relevant medical history (up to 50 words).",
    )

    class Meta(Person.Meta):
        pass

    def get_absolute_url(self) -> str:
        return reverse("records:patient_detail", args=[self.pk])

    @property
    def age(self) -> int:
        today = timezone.localdate()
        birthday = self.date_of_birth
        return today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))

    @property
    def initials(self) -> str:
        return f"{self.first_name[:1]}.{self.last_name[:1]}."

    def clean(self) -> None:
        super().clean()
        if self.date_of_birth and self.date_of_birth > timezone.localdate():
            raise ValidationError({"date_of_birth": "Date of birth cannot be in the future."})


class Inpatient(Patient):
    """Multi-table inheritance: a Patient who has been admitted.

    Django creates an implicit ``OneToOneField`` primary key pointing back to
    ``Patient``, so ``inpatient.patient_ptr`` and ``inpatient.first_name`` both work.
    """

    admitted_on = models.DateField(default=timezone.localdate)
    discharged_on = models.DateField(null=True, blank=True)
    ward = models.CharField(max_length=60, blank=True)
    room_number = models.CharField(max_length=10, blank=True)
    daily_rate = models.DecimalField(max_digits=8, decimal_places=2, default=150.00)

    class Meta:
        ordering = ("-admitted_on",)
        verbose_name = "admitted patient"

    @property
    def is_currently_admitted(self) -> bool:
        return self.discharged_on is None

    @property
    def length_of_stay(self) -> int:
        end = self.discharged_on or timezone.localdate()
        return max((end - self.admitted_on).days, 0)

    @property
    def estimated_bill(self) -> float:
        return float(self.length_of_stay * self.daily_rate)

    def clean(self) -> None:
        super().clean()
        if self.discharged_on and self.discharged_on < self.admitted_on:
            raise ValidationError({"discharged_on": "Discharge date cannot be before admission."})

    def __str__(self) -> str:
        state = "admitted" if self.is_currently_admitted else "discharged"
        return f"{self.full_name} [{state}]"


class PatientDirectory(Patient):
    """Proxy model: same table, friendlier default ordering for directories."""

    class Meta:
        proxy = True
        ordering = ("first_name", "last_name")
        verbose_name = "patient directory entry"


class Appointment(TimeStampedModel):
    """A scheduled meeting between a patient and a doctor."""

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("no_show", "No show"),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="appointments")
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30, validators=[MinValueValidator(5)])
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="scheduled")
    reason = models.CharField(
        max_length=200,
        validators=[max_words(15)],
        help_text="Why the patient is visiting (up to 15 words).",
    )
    notes = models.TextField(blank=True, validators=[max_words(100)],
                             help_text="Optional notes (up to 100 words).")

    class Meta:
        ordering = ("-scheduled_at",)

    def get_absolute_url(self) -> str:
        return reverse("records:appointment_detail", args=[self.pk])

    @property
    def is_upcoming(self) -> bool:
        return self.scheduled_at >= timezone.now() and self.status == "scheduled"

    @property
    def ends_at(self):
        return self.scheduled_at + timedelta(minutes=self.duration_minutes)

    def clean(self) -> None:
        super().clean()
        if (
            self.patient_id
            and self.doctor_id
            and Appointment.objects.filter(
                patient=self.patient, doctor=self.doctor, scheduled_at=self.scheduled_at
            ).exclude(pk=self.pk).exists()
        ):
            raise ValidationError("That doctor already has this patient booked at that time.")

    def __str__(self) -> str:
        return f"{self.patient} → {self.doctor} @ {self.scheduled_at:%Y-%m-%d %H:%M}"


class MedicalNote(TimeStampedModel):
    """Clinical note text — where our own ``texttools`` package gets used."""

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="notes")
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name="notes")
    title = models.CharField(max_length=120)
    body = models.TextField(
        validators=[min_words(3), max_words(120)],
        help_text="Between 3 and 120 words — counted with texttools.",
    )

    class Meta:
        ordering = ("-created_at",)

    @property
    def word_count(self) -> int:
        return texttools.count_words(self.body)

    @property
    def character_count(self) -> int:
        return texttools.count_characters(self.body)

    @property
    def summary(self) -> str:
        """First sentence-ish snippet, title-cased — a texttools demo."""
        return texttools.truncate(texttools.capitalize_words(self.body), length=120)

    @property
    def title_is_palindrome(self) -> bool:
        return texttools.is_palindrome(self.title)

    def get_absolute_url(self) -> str:
        return reverse("records:patient_detail", args=[self.patient_id])

    def __str__(self) -> str:
        return f"{self.title} — {self.patient}"
