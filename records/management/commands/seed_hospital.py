"""Seed the database with demo hospital data.

Usage:  python manage.py seed_hospital [--clear]
"""

from __future__ import annotations

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from records.models import Appointment, Department, Doctor, Inpatient, MedicalNote, Patient

FIRST = ["Amina", "John", "Zara", "Peter", "Lena", "Omar", "Grace", "Mateo", "Ivy", "Noah", "Ruth", "Kenji",
         "Sara", "Tariq", "Nadia", "Felix"]
LAST = ["Rahman", "Doe", "Khan", "Mwangi", "Novak", "Hassan", "Lopez", "Smith", "Parikh", "Silva", "Racecar", "Otto",
        "Anna", "Kayak", "Level", "Stats"]
REASONS = [
    "Annual checkup and blood pressure review",
    "Follow-up after surgery",
    "Persistent cough and mild fever",
    "Sports injury to the knee",
    "Blood work and cholesterol screening",
    "Migraine that will not go away",
    "Routine vaccination for the child",
]
NOTE_BODIES = [
    "Patient reports steady improvement. Continue current medication and revisit in two weeks.",
    "Blood pressure slightly elevated today. Advised low sodium diet and daily walks.",
    "Follow up with radiology for the chest x ray results before the next consultation.",
    "level up with racecar fun",
]


def make_patient(index: int) -> dict:
    first, last = FIRST[index % len(FIRST)], LAST[index % len(LAST)]
    year = 1960 + (index * 4) % 60
    return dict(
        first_name=first,
        last_name=last,
        email=f"{first.lower()}.{last.lower()}{index}@example.com",
        phone=f"+1 555 12{index:03d}",
        address=f"{100 + index} Maple Street",
        date_of_birth=timezone.localdate().replace(
            year=year, month=(index % 12) + 1, day=(index % 27) + 1
        ),
        gender=["f", "m", "other"][index % 3],
        blood_group=Patient.BLOOD_GROUPS[index % len(Patient.BLOOD_GROUPS)],
        allergies="penicillin" if index % 4 == 0 else "",
        medical_history="Hypertension managed with medication." if index % 3 == 0 else "",
    )


class Command(BaseCommand):
    help = "Create demo departments, doctors, patients, admissions, appointments and notes."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Delete existing records first.")

    def handle(self, *args, **options):
        if options["clear"]:
            MedicalNote.objects.all().delete()
            Appointment.objects.all().delete()
            Inpatient.objects.all().delete()
            Patient.objects.all().delete()
            Doctor.objects.all().delete()
            Department.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing records."))

        random.seed(42)  # deterministic data so the demo is repeatable

        departments = Department.objects.bulk_create([
            Department(name="Cardiology", code="CARD", location="Block A, Floor 3",
                       description="Heart and circulatory care for adults."),
            Department(name="Pediatrics", code="PEDS", location="Block B, Floor 1",
                       description="Care for infants, children and teenagers."),
            Department(name="Emergency", code="ER", location="Ground floor, east wing",
                       description="24/7 emergency and trauma admissions."),
            Department(name="Radiology", code="RAD", location="Block C, Floor 2",
                       description="Imaging: x-ray, MRI and ultrasound."),
        ])

        specialties = [code for code, _ in Doctor.SPECIALTIES]
        doctors = [
            Doctor(
                first_name=FIRST[index],
                last_name=LAST[(index * 3) % len(LAST)],
                email=f"dr.{FIRST[index].lower()}{index}@riverside.example",
                phone=f"+1 555 01{index:03d}",
                specialty=specialties[index % len(specialties)],
                license_number=f"LIC-{2020 + index}-{random.randint(1000, 9999)}",
                department=random.choice(departments),
            )
            for index in range(8)
        ]
        Doctor.objects.bulk_create(doctors)
        doctors = list(Doctor.objects.all())

        # 12 outpatients
        patients = Patient.objects.bulk_create([Patient(**make_patient(i)) for i in range(12)])
        patients = list(Patient.objects.all())

        # 4 inpatients — multi-table inheritance creates two rows each
        # (one in records_patient, one in records_inpatient linked by patient_ptr).
        inpatient_rows = [
            Inpatient(**make_patient(12 + i),
                      admitted_on=(timezone.localdate() - timedelta(days=6 - i)),
                      discharged_on=None if i < 3 else (timezone.localdate() - timedelta(days=2)),
                      ward=["Blue", "Green", "Red", "Blue"][i],
                      room_number=f"{300 + i}",
                      daily_rate=[150, 180, 220, 150][i])
            for i in range(4)
        ]
        for row in inpatient_rows:
            row.save()
        inpatient_rows = list(Inpatient.objects.all())

        now = timezone.now()
        everyone = patients + list(inpatient_rows)
        appointments = [
            Appointment(
                patient=random.choice(everyone),
                doctor=random.choice(doctors),
                scheduled_at=(now + timedelta(hours=3 * (index - 5), days=index % 4))
                .replace(minute=0, second=0, microsecond=0),
                duration_minutes=random.choice([15, 30, 45, 60]),
                status=random.choice(["scheduled", "completed", "cancelled", "no_show"]),
                reason=random.choice(REASONS),
            )
            for index in range(14)
        ]
        Appointment.objects.bulk_create(appointments)

        MedicalNote.objects.bulk_create([
            MedicalNote(
                patient=random.choice(everyone),
                doctor=random.choice(doctors),
                title=f"Consultation note {index + 1}",
                body=body,
            )
            for index, body in enumerate(NOTE_BODIES)
        ])

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(departments)} departments, {len(doctors)} doctors, "
            f"{len(patients)} outpatients, {len(inpatient_rows)} inpatients, "
            f"{Appointment.objects.count()} appointments and {len(NOTE_BODIES)} notes."
        ))
