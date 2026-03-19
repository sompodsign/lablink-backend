"""
Management command to seed E2E test data.

Creates tenants, users with all roles, and links them — idempotent (get_or_create).
Usage:  python manage.py seed_e2e
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.tenants.models import DiagnosticCenter, Doctor, Permission, Role, Staff
from core.users.models import PatientProfile

logger = logging.getLogger(__name__)
User = get_user_model()

# Permissions each role should have (None = all permissions)
DEFAULT_ROLE_PERMS: dict[str, list[str] | None] = {
    "Admin": None,
    "Medical Technologist": [
        "view_patients",
        "view_reports",
        "create_reports",
        "manage_reports",
        "view_test_orders",
        "manage_test_orders",
    ],
    "Receptionist": [
        "view_patients",
        "manage_patients",
        "view_appointments",
        "manage_appointments",
        "view_reports",
        "view_payments",
        "manage_payments",
    ],
    "Doctor": [
        "view_patients",
        "view_appointments",
        "manage_appointments",
        "view_test_orders",
        "view_reports",
        "create_reports",
    ],
}

PASSWORD = "TestPass123!"

CENTERS = [
    {
        "domain": "alpha-lab",
        "name": "Alpha Diagnostics",
        "address": "42 Gulshan Avenue, Dhaka-1212",
        "contact_number": "01711111111",
        "email": "info@alpha.lab",
    },
    {
        "domain": "beta-lab",
        "name": "Beta Medical Lab",
        "address": "18 Dhanmondi R/A, Dhaka-1205",
        "contact_number": "01722222222",
        "email": "info@beta.lab",
    },
]

USERS_CONFIG = [
    # Alpha Lab
    {
        "username": "e2e_alpha_admin",
        "email": "alpha.admin@lablink.test",
        "first_name": "Rahim",
        "last_name": "Khan",
        "phone": "01711000001",
        "is_staff": True,
        "center": "alpha-lab",
        "role": "ADMIN",
    },
    {
        "username": "e2e_alpha_receptionist",
        "email": "alpha.recep@lablink.test",
        "first_name": "Ayesha",
        "last_name": "Begum",
        "phone": "01711000002",
        "center": "alpha-lab",
        "role": "RECEPTIONIST",
    },
    {
        "username": "e2e_alpha_labtech",
        "email": "alpha.tech@lablink.test",
        "first_name": "Karim",
        "last_name": "Hossain",
        "phone": "01711000003",
        "center": "alpha-lab",
        "role": "MEDICAL_TECHNOLOGIST",
    },
    {
        "username": "e2e_alpha_doctor",
        "email": "alpha.doc@lablink.test",
        "first_name": "Farhan",
        "last_name": "Ahmed",
        "phone": "01711000004",
        "center": "alpha-lab",
        "doctor": {"specialization": "Hematology", "designation": "Senior Consultant"},
    },
    {
        "username": "e2e_alpha_patient1",
        "email": "alpha.pat1@lablink.test",
        "first_name": "Nasreen",
        "last_name": "Akter",
        "phone": "01711000005",
        "center": "alpha-lab",
        "patient": {
            "dob": "1988-03-15",
            "gender": "F",
            "blood_group": "B+",
            "address": "12 Mirpur, Dhaka",
        },
    },
    {
        "username": "e2e_alpha_patient2",
        "email": "alpha.pat2@lablink.test",
        "first_name": "Imran",
        "last_name": "Uddin",
        "phone": "01711000006",
        "center": "alpha-lab",
        "patient": {
            "dob": "1995-07-22",
            "gender": "M",
            "blood_group": "O+",
            "address": "5/A Uttara, Dhaka",
        },
    },
    # Beta Lab
    {
        "username": "e2e_beta_admin",
        "email": "beta.admin@lablink.test",
        "first_name": "Sakib",
        "last_name": "Rahman",
        "phone": "01722000001",
        "is_staff": True,
        "center": "beta-lab",
        "role": "ADMIN",
    },
    {
        "username": "e2e_beta_receptionist",
        "email": "beta.recep@lablink.test",
        "first_name": "Fatima",
        "last_name": "Khatun",
        "phone": "01722000002",
        "center": "beta-lab",
        "role": "RECEPTIONIST",
    },
    {
        "username": "e2e_beta_labtech",
        "email": "beta.tech@lablink.test",
        "first_name": "Tanvir",
        "last_name": "Hasan",
        "phone": "01722000003",
        "center": "beta-lab",
        "role": "MEDICAL_TECHNOLOGIST",
    },
    {
        "username": "e2e_beta_doctor",
        "email": "beta.doc@lablink.test",
        "first_name": "Nadia",
        "last_name": "Sultana",
        "phone": "01722000004",
        "center": "beta-lab",
        "doctor": {"specialization": "Pathology", "designation": "Consultant"},
    },
    {
        "username": "e2e_beta_patient1",
        "email": "beta.pat1@lablink.test",
        "first_name": "Rashid",
        "last_name": "Mia",
        "phone": "01722000005",
        "center": "beta-lab",
        "patient": {
            "dob": "1992-11-08",
            "gender": "M",
            "blood_group": "A-",
            "address": "33 Mohammadpur, Dhaka",
        },
    },
    # Superadmin
    {
        "username": "e2e_superadmin",
        "email": "super@lablink.test",
        "first_name": "Super",
        "last_name": "Admin",
        "phone": "01700000000",
        "is_staff": True,
        "is_superuser": True,
    },
]


class Command(BaseCommand):
    help = "Seed E2E test data (tenants, users with all roles). Idempotent."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_e2e can only run with DEBUG=True.")

        centers = self._create_centers()
        self._create_roles(centers)
        self._create_users(centers)

        self.stdout.write(
            self.style.SUCCESS(f"\n✅ E2E seed complete — all passwords: {PASSWORD}")
        )

    def _create_centers(self):
        self.stdout.write("--- Centers ---")
        centers = {}
        for cfg in CENTERS:
            center, created = DiagnosticCenter.objects.get_or_create(
                domain=cfg["domain"],
                defaults={k: v for k, v in cfg.items() if k != "domain"},
            )
            tag = "CREATED" if created else "EXISTS"
            self.stdout.write(f"  [{tag}] {center.name}")
            centers[cfg["domain"]] = center
        return centers

    def _create_roles(self, centers):
        """Ensure every center has all default roles with correct permissions."""
        self.stdout.write("--- Roles ---")
        all_perms = {p.codename: p for p in Permission.objects.all()}
        for center in centers.values():
            for role_name, perm_codenames in DEFAULT_ROLE_PERMS.items():
                role, created = Role.objects.get_or_create(
                    name=role_name,
                    center=center,
                    defaults={"is_system": True},
                )
                # Always sync permissions
                if perm_codenames is None:
                    role.permissions.set(all_perms.values())
                else:
                    role.permissions.set(
                        [all_perms[c] for c in perm_codenames if c in all_perms]
                    )
                tag = "CREATED" if created else "SYNCED"
                self.stdout.write(f"  [{tag}] {role_name} → {center.name}")

    def _create_users(self, centers):
        self.stdout.write("--- Users ---")
        for cfg in USERS_CONFIG:
            user, created = User.objects.get_or_create(
                username=cfg["username"],
                defaults={
                    "email": cfg["email"],
                    "first_name": cfg["first_name"],
                    "last_name": cfg["last_name"],
                    "phone_number": cfg.get("phone", ""),
                    "is_staff": cfg.get("is_staff", False),
                    "is_superuser": cfg.get("is_superuser", False),
                },
            )
            if created:
                user.set_password(PASSWORD)
                user.save()

            tag = "CREATED" if created else "EXISTS"
            self.stdout.write(f"  [{tag}] {cfg['username']}")

            center_domain = cfg.get("center")
            center = centers.get(center_domain) if center_domain else None

            # Set user.center for non-superadmins
            if center and user.center_id != center.id:
                user.center = center
                user.save(update_fields=["center_id"])

            if not center:
                continue

            # Staff role
            role_name = cfg.get("role")
            if role_name:
                role_map = {
                    "ADMIN": "Admin",
                    "RECEPTIONIST": "Receptionist",
                    "MEDICAL_TECHNOLOGIST": "Medical Technologist",
                }
                mapped_name = role_map.get(role_name, role_name)
                role_obj, role_created = Role.objects.get_or_create(
                    name=mapped_name,
                    center=center,
                    defaults={"is_system": True},
                )
                # Assign permissions (always sync to match DEFAULT_ROLE_PERMS)
                perm_codenames = DEFAULT_ROLE_PERMS.get(mapped_name)
                if perm_codenames is None:
                    # Admin → all permissions
                    role_obj.permissions.set(Permission.objects.all())
                elif perm_codenames:
                    role_obj.permissions.set(
                        Permission.objects.filter(codename__in=perm_codenames)
                    )
                Staff.objects.get_or_create(
                    user=user,
                    defaults={"center": center, "role": role_obj},
                )

            # Doctor
            doctor_cfg = cfg.get("doctor")
            if doctor_cfg:
                Doctor.objects.get_or_create(
                    user=user,
                    defaults={
                        "specialization": doctor_cfg["specialization"],
                        "designation": doctor_cfg["designation"],
                        "bio": "",
                    },
                )

            # Patient
            patient_cfg = cfg.get("patient")
            if patient_cfg:
                PatientProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "phone_number": cfg.get("phone", ""),
                        "date_of_birth": patient_cfg["dob"],
                        "gender": patient_cfg["gender"],
                        "blood_group": patient_cfg["blood_group"],
                        "address": patient_cfg["address"],
                        "registered_at_center": center,
                    },
                )
