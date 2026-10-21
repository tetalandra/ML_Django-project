"""URLs for the records app: full CRUD routes for every model."""

from django.urls import path

from . import views

app_name = "records"

urlpatterns = [
    # Patients
    path("patients/", views.PatientListView.as_view(), name="patient_list"),
    path("patients/new/", views.PatientCreateView.as_view(), name="patient_create"),
    path("patients/<int:pk>/", views.PatientDetailView.as_view(), name="patient_detail"),
    path("patients/<int:pk>/edit/", views.PatientUpdateView.as_view(), name="patient_update"),
    path("patients/<int:pk>/delete/", views.PatientDeleteView.as_view(), name="patient_delete"),
    # Doctors
    path("doctors/", views.DoctorListView.as_view(), name="doctor_list"),
    path("doctors/new/", views.DoctorCreateView.as_view(), name="doctor_create"),
    path("doctors/<int:pk>/", views.DoctorDetailView.as_view(), name="doctor_detail"),
    path("doctors/<int:pk>/edit/", views.DoctorUpdateView.as_view(), name="doctor_update"),
    path("doctors/<int:pk>/delete/", views.DoctorDeleteView.as_view(), name="doctor_delete"),
    # Appointments
    path("appointments/", views.AppointmentListView.as_view(), name="appointment_list"),
    path("appointments/new/", views.AppointmentCreateView.as_view(), name="appointment_create"),
    path("appointments/<int:pk>/", views.AppointmentDetailView.as_view(), name="appointment_detail"),
    path("appointments/<int:pk>/edit/", views.AppointmentUpdateView.as_view(), name="appointment_update"),
    path("appointments/<int:pk>/delete/", views.AppointmentDeleteView.as_view(), name="appointment_delete"),
    # Departments
    path("departments/", views.DepartmentListView.as_view(), name="department_list"),
    path("departments/new/", views.DepartmentCreateView.as_view(), name="department_create"),
    path("departments/<int:pk>/", views.DepartmentDetailView.as_view(), name="department_detail"),
    path("departments/<int:pk>/edit/", views.DepartmentUpdateView.as_view(), name="department_update"),
    path("departments/<int:pk>/delete/", views.DepartmentDeleteView.as_view(), name="department_delete"),
]
