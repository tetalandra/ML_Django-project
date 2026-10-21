"""Admin configuration: list displays, inlines and searchable columns."""

from django.contrib import admin

from .models import Appointment, Department, Doctor, Inpatient, MedicalNote, Patient, PatientDirectory


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "location", "created_at")
    search_fields = ("name", "code", "location")


class DoctorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "specialty", "license_number", "department")
    list_filter = ("specialty", "department")
    search_fields = ("first_name", "last_name", "email", "license_number")


admin.site.register(Doctor, DoctorAdmin)


class AppointmentInline(admin.TabularInline):
    model = Appointment
    extra = 0
    fields = ("doctor", "scheduled_at", "status", "reason")


class MedicalNoteInline(admin.StackedInline):
    model = MedicalNote
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "date_of_birth", "gender", "blood_group", "email")
    list_filter = ("gender", "blood_group")
    search_fields = ("first_name", "last_name", "email")
    inlines = (AppointmentInline, MedicalNoteInline)
    date_hierarchy = "date_of_birth"


@admin.register(Inpatient)
class InpatientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "ward", "room_number", "admitted_on", "discharged_on", "daily_rate")
    list_filter = ("ward",)
    search_fields = ("first_name", "last_name", "room_number")


@admin.register(PatientDirectory)
class PatientDirectoryAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone")
    search_fields = ("first_name", "last_name")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "scheduled_at", "status")
    list_filter = ("status", "doctor")
    search_fields = ("patient__first_name", "patient__last_name", "reason")
    list_select_related = ("patient", "doctor")


@admin.register(MedicalNote)
class MedicalNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "patient", "doctor", "created_at")
    search_fields = ("title", "body", "patient__last_name")
