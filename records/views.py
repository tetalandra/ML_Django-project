"""CRUD views built on Django generic class-based views.

List + search, detail, create, update and delete for every main model,
plus a few "advanced behind the scenes" extras:

* multi-field search with ``?q=``
* flash messages after every create/update/delete
* ``get_success_url()`` through each model's ``get_absolute_url()``
* inline creation of a medical note from the patient detail page
"""

from __future__ import annotations

from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from core.mixins import GroupRequiredMixin

from .forms import AppointmentForm, DepartmentForm, DoctorForm, MedicalNoteForm, PatientForm
from .models import Appointment, Department, Doctor, MedicalNote, Patient

# ---- group-based access (core/mixins.py + `manage.py setup_groups`) ----
CLINICIANS = ("Clinicians",)
OPERATIONS = ("Operations",)
CLINICIAN_OR_OPS = CLINICIANS + OPERATIONS


class SearchListMixin:
    """Adds a ``?q=`` search box over several model fields."""

    search_fields: list[str] = []
    query_param = "q"

    def get_queryset(self):
        qs = super().get_queryset()
        term = self.request.GET.get(self.query_param, "").strip()
        if term and self.search_fields:
            condition = Q()
            for field in self.search_fields:
                condition |= Q(**{f"{field}__icontains": term})
            qs = qs.filter(condition)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get(self.query_param, "").strip()
        return ctx


class FlashMessageMixin:
    """Shows a success message after create/update/delete."""

    success_message = ""

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response


# --------------------------------------------------------------------------- Patients
class PatientListView(GroupRequiredMixin, SearchListMixin, ListView):
    allowed_groups = CLINICIANS
    model = Patient
    context_object_name = "patients"
    paginate_by = 10
    search_fields = ["first_name", "last_name", "email", "phone", "blood_group"]

    def get_queryset(self):
        return super().get_queryset().select_related()


class PatientDetailView(GroupRequiredMixin, DetailView):
    allowed_groups = CLINICIANS
    model = Patient
    context_object_name = "patient"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["appointments"] = self.object.appointments.select_related("doctor")[:10]
        ctx["notes"] = self.object.notes.select_related("doctor")
        ctx["note_form"] = MedicalNoteForm(prefix="note")
        ctx["is_inpatient"] = hasattr(self.object, "inpatient")
        if ctx["is_inpatient"]:
            ctx["inpatient"] = self.object.inpatient
        return ctx


class PatientCreateView(GroupRequiredMixin, FlashMessageMixin, CreateView):
    allowed_groups = CLINICIANS
    model = Patient
    form_class = PatientForm
    success_message = "Patient created."


class PatientUpdateView(GroupRequiredMixin, FlashMessageMixin, UpdateView):
    allowed_groups = CLINICIANS
    model = Patient
    form_class = PatientForm
    success_message = "Patient updated."


class PatientDeleteView(GroupRequiredMixin, FlashMessageMixin, DeleteView):
    allowed_groups = CLINICIANS
    model = Patient
    success_url = reverse_lazy("records:patient_list")
    success_message = "Patient deleted."


# --------------------------------------------------------------------------- Doctors
class DoctorListView(GroupRequiredMixin, SearchListMixin, ListView):
    allowed_groups = CLINICIAN_OR_OPS
    model = Doctor
    context_object_name = "doctors"
    paginate_by = 10
    search_fields = ["first_name", "last_name", "email", "specialty", "department__name"]

    def get_queryset(self):
        return super().get_queryset().select_related("department")


class DoctorDetailView(GroupRequiredMixin, DetailView):
    allowed_groups = CLINICIAN_OR_OPS
    model = Doctor
    context_object_name = "doctor"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["appointments"] = self.object.appointments.select_related("patient")[:10]
        return ctx


class DoctorCreateView(GroupRequiredMixin, FlashMessageMixin, CreateView):
    allowed_groups = OPERATIONS
    model = Doctor
    form_class = DoctorForm
    success_message = "Doctor created."


class DoctorUpdateView(GroupRequiredMixin, FlashMessageMixin, UpdateView):
    allowed_groups = OPERATIONS
    model = Doctor
    form_class = DoctorForm
    success_message = "Doctor updated."


class DoctorDeleteView(GroupRequiredMixin, FlashMessageMixin, DeleteView):
    allowed_groups = OPERATIONS
    model = Doctor
    success_url = reverse_lazy("records:doctor_list")
    success_message = "Doctor deleted."


# --------------------------------------------------------------------------- Appointments
class AppointmentListView(GroupRequiredMixin, SearchListMixin, ListView):
    allowed_groups = CLINICIAN_OR_OPS
    model = Appointment
    context_object_name = "appointments"
    paginate_by = 10
    search_fields = ["patient__first_name", "patient__last_name", "doctor__last_name", "reason", "status"]

    def get_queryset(self):
        return super().get_queryset().select_related("patient", "doctor")


class AppointmentDetailView(GroupRequiredMixin, DetailView):
    allowed_groups = CLINICIAN_OR_OPS
    model = Appointment
    context_object_name = "appointment"

    def get_queryset(self):
        return super().get_queryset().select_related("patient", "doctor")


class AppointmentCreateView(GroupRequiredMixin, FlashMessageMixin, CreateView):
    allowed_groups = CLINICIANS
    model = Appointment
    form_class = AppointmentForm
    success_message = "Appointment booked."

    def get_initial(self):
        initial = super().get_initial()
        if patient_id := self.request.GET.get("patient"):
            initial["patient"] = patient_id
        return initial


class AppointmentUpdateView(GroupRequiredMixin, FlashMessageMixin, UpdateView):
    allowed_groups = CLINICIANS
    model = Appointment
    form_class = AppointmentForm
    success_message = "Appointment updated."


class AppointmentDeleteView(GroupRequiredMixin, FlashMessageMixin, DeleteView):
    allowed_groups = CLINICIANS
    model = Appointment
    success_url = reverse_lazy("records:appointment_list")
    success_message = "Appointment deleted."


# --------------------------------------------------------------------------- Departments
class DepartmentListView(GroupRequiredMixin, SearchListMixin, ListView):
    allowed_groups = OPERATIONS
    model = Department
    context_object_name = "departments"
    paginate_by = 10
    search_fields = ["name", "code", "location"]

    def get_queryset(self):
        return super().get_queryset().prefetch_related("doctors")


class DepartmentDetailView(GroupRequiredMixin, DetailView):
    allowed_groups = OPERATIONS
    model = Department
    context_object_name = "department"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["doctors"] = self.object.doctors.all()
        return ctx


class DepartmentCreateView(GroupRequiredMixin, FlashMessageMixin, CreateView):
    allowed_groups = OPERATIONS
    model = Department
    form_class = DepartmentForm
    success_message = "Department created."


class DepartmentUpdateView(GroupRequiredMixin, FlashMessageMixin, UpdateView):
    allowed_groups = OPERATIONS
    model = Department
    form_class = DepartmentForm
    success_message = "Department updated."


class DepartmentDeleteView(GroupRequiredMixin, FlashMessageMixin, DeleteView):
    allowed_groups = OPERATIONS
    model = Department
    success_url = reverse_lazy("records:department_list")
    success_message = "Department deleted."
