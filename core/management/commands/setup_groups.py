"""Create the two access-control groups (and optional demo users).

Usage:
    python manage.py setup_groups                 # create/refresh groups + permissions
    python manage.py setup_groups --demo-users    # also create clinician / opsdesk logins

Groups:
    Clinicians  patients (full), appointments (full), medical notes, doctor list
    Operations  doctors (full), departments (full), appointment oversight (read-only)
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

# codenames are all in the `records` app
CLINICIAN_PERMS = [
    # patients — full CRUD
    "view_patient", "add_patient", "change_patient", "delete_patient",
    # appointments — full CRUD
    "view_appointment", "add_appointment", "change_appointment", "delete_appointment",
    # clinical notes — read + write (deleting is a clinician-supervisor job)
    "view_medicalnote", "add_medicalnote", "change_medicalnote",
    # doctors: read-only (needed to book an appointment)
    "view_doctor",
]

OPERATION_PERMS = [
    # doctors — full CRUD
    "view_doctor", "add_doctor", "change_doctor", "delete_doctor",
    # departments — full CRUD
    "view_department", "add_department", "change_department", "delete_department",
    # appointments: read-only oversight (booking stays with Clinicians)
    "view_appointment",
]

DEMO_USERS = [
    # (username, password, group)
    ("clinician", "clin12345!", "Clinicians"),
    ("opsdesk", "ops12345!", "Operations"),
]


class Command(BaseCommand):
    help = "Create the Clinicians and Operations groups with their permissions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo-users",
            action="store_true",
            help="Also create demo logins (clinician / opsdesk).",
        )

    def handle(self, *args, **options):
        for name, codenames in (
            ("Clinicians", CLINICIAN_PERMS),
            ("Operations", OPERATION_PERMS),
        ):
            group, created = Group.objects.get_or_create(name=name)
            perms = Permission.objects.filter(
                content_type__app_label="records", codename__in=codenames
            )
            missing = set(codenames) - set(perms.values_list("codename", flat=True))
            group.permissions.set(perms)
            verb = "Created" if created else "Refreshed"
            self.stdout.write(self.style.SUCCESS(
                f"{verb} group '{name}' with {perms.count()} permissions"
            ))
            if missing:
                self.stdout.write(self.style.WARNING(
                    f"  (unknown codenames skipped: {', '.join(sorted(missing))})"
                ))

        if options["demo_users"]:
            User = get_user_model()
            for username, password, group_name in DEMO_USERS:
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={"email": f"{username}@riverside.example"},
                )
                user.set_password(password)
                user.is_staff = False
                user.is_superuser = False
                user.save()
                user.groups.set([Group.objects.get(name=group_name)])
                verb = "Created" if created else "Updated"
                self.stdout.write(self.style.SUCCESS(
                    f"{verb} demo user '{username}' (group: {group_name})"
                ))
