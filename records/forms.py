"""ModelForms for the hospital CRUD screens, with real validation logic."""

from __future__ import annotations

from django import forms
from django.core.exceptions import FieldDoesNotExist, ValidationError

from .models import Appointment, Department, Doctor, Inpatient, MedicalNote, Patient

DATE_INPUT = {"type": "date"}
DATETIME_INPUT = {"type": "datetime-local"}


class StyledModelForm(forms.ModelForm):
    """Adds our plain-CSS ``field`` class to every widget.

    Fields that carry a texttools word-limit validator also get a
    ``data-word-limit`` / ``data-word-min`` attribute so the browser can show
    a live "12 / 50 words" counter while typing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model = self._meta.model
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} field".strip()
            if isinstance(field.widget, forms.DateTimeInput):
                field.widget.attrs.setdefault("type", "datetime-local")
            if isinstance(field.widget, forms.DateInput):
                field.widget.attrs.setdefault("type", "date")
            # Word limits live on the model field; expose them to the browser.
            try:
                model_field = model._meta.get_field(name)
            except FieldDoesNotExist:
                continue
            for validator in getattr(model_field, "validators", []):
                if hasattr(validator, "limit"):
                    field.widget.attrs["data-word-limit"] = validator.limit
                if hasattr(validator, "min_limit"):
                    field.widget.attrs["data-word-min"] = validator.min_limit


class PatientForm(StyledModelForm):
    class Meta:
        model = Patient
        fields = [
            "first_name", "last_name", "email", "phone", "address",
            "date_of_birth", "gender", "blood_group", "allergies", "medical_history",
        ]


class InpatientForm(StyledModelForm):
    class Meta:
        model = Inpatient
        fields = PatientForm.Meta.fields + [
            "admitted_on", "discharged_on", "ward", "room_number", "daily_rate",
        ]

    def clean(self):
        cleaned = super().clean()
        admitted = cleaned.get("admitted_on")
        discharged = cleaned.get("discharged_on")
        if admitted and discharged and discharged < admitted:
            raise ValidationError({"discharged_on": "Discharge date cannot be before admission."})
        return cleaned


class DoctorForm(StyledModelForm):
    class Meta:
        model = Doctor
        fields = [
            "first_name", "last_name", "email", "phone", "address",
            "specialty", "license_number", "department",
        ]


class DepartmentForm(StyledModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "location", "description"]

    def clean_code(self):
        code = self.cleaned_data["code"].upper()
        if len(code) < 2:
            raise ValidationError("Code must be at least 2 characters.")
        return code


class AppointmentForm(StyledModelForm):
    class Meta:
        model = Appointment
        fields = ["patient", "doctor", "scheduled_at", "duration_minutes", "status", "reason", "notes"]
        widgets = {"scheduled_at": forms.DateTimeInput(attrs=DATETIME_INPUT)}

    def clean(self):
        cleaned = super().clean()
        patient = cleaned.get("patient")
        doctor = cleaned.get("doctor")
        when = cleaned.get("scheduled_at")
        if patient and doctor and when:
            clash = (
                Appointment.objects.filter(patient=patient, doctor=doctor, scheduled_at=when)
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if clash:
                raise ValidationError("That doctor already has this patient booked at that time.")
        return cleaned


class MedicalNoteForm(StyledModelForm):
    class Meta:
        model = MedicalNote
        fields = ["title", "body", "doctor"]
