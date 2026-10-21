"""URLs for the core app: dashboard, medical note POST."""

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("patients/<int:patient_pk>/notes/new/", views.AddMedicalNoteView.as_view(), name="add_note"),
]
