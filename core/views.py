"""Dashboard view for the core app."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from records.forms import MedicalNoteForm
from records.models import Appointment, Department, Doctor, Inpatient, Patient

from .mixins import GroupRequiredMixin, user_in_groups
from .services import dashboard_insights

CLINICIANS = ("Clinicians",)
OPERATIONS = ("Operations",)

class DashboardView(LoginRequiredMixin, View):
    """Home page: a few live numbers and simple insights.

    Login is required (group access control); the patient panel is only
    shown to the Clinicians group, while Operations gets its own
    quick action instead.
    """

    def get(self, request):
        today = timezone.localdate()
        now = timezone.now()
        show_clinical = user_in_groups(request.user, CLINICIANS)
        show_operations = user_in_groups(request.user, OPERATIONS)
        context = {
            "show_clinical": show_clinical,
            "show_operations": show_operations,
            "user_groups": [g.name for g in request.user.groups.all()] or (["Superuser"] if request.user.is_superuser else []),
            "patient_count": Patient.objects.count(),
            "doctor_count": Doctor.objects.count(),
            "department_count": Department.objects.count(),
            "appointment_count": Appointment.objects.count(),
            "admitted_count": Inpatient.objects.filter(discharged_on__isnull=True).count(),
            "appointments_today": Appointment.objects.filter(
                scheduled_at__date=today, status="scheduled"
            ).count(),
            "upcoming": Appointment.objects.filter(scheduled_at__gte=now, status="scheduled")
            .select_related("patient", "doctor")[:6],
            "recent_patients": Patient.objects.order_by("-created_at")[:6] if show_clinical else [],
            "insights": dashboard_insights(),
        }
        return render(request, "core/dashboard.html", context)


class AddMedicalNoteView(GroupRequiredMixin, View):
    """POST-only endpoint used by the patient detail page (Clinicians only)."""

    allowed_groups = CLINICIANS

    def post(self, request, patient_pk):
        patient = Patient.objects.get(pk=patient_pk)
        form = MedicalNoteForm(request.POST, prefix="note")
        if form.is_valid():
            note = form.save(commit=False)
            note.patient = patient
            note.save()
            messages.success(request, "Medical note added.")
        else:
            messages.error(request, "Could not save the note: " + "; ".join(
                error for errors in form.errors.values() for error in errors
            ))
        return redirect(patient)
