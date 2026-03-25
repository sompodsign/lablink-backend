"""
Data migration: add "Medical Assistant" system role to every existing center.
"""

from django.db import migrations

MEDICAL_ASSISTANT_PERMS = [
    "view_patients",
    "manage_patients",
    "view_appointments",
    "manage_appointments",
    "view_reports",
    "view_test_orders",
    "view_payments",
]


def add_medical_assistant_role(apps, _schema_editor):
    DiagnosticCenter = apps.get_model("tenants", "DiagnosticCenter")
    Role = apps.get_model("tenants", "Role")
    Permission = apps.get_model("tenants", "Permission")

    perms = list(Permission.objects.filter(codename__in=MEDICAL_ASSISTANT_PERMS))

    for center in DiagnosticCenter.objects.all():
        role, _created = Role.objects.update_or_create(
            name="Medical Assistant",
            center=center,
            defaults={"is_system": True},
        )
        role.permissions.set(perms)


def remove_medical_assistant_role(apps, _schema_editor):
    Role = apps.get_model("tenants", "Role")
    Role.objects.filter(name="Medical Assistant", is_system=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0020_add_notification_flags"),
    ]

    operations = [
        migrations.RunPython(
            add_medical_assistant_role,
            reverse_code=remove_medical_assistant_role,
        ),
    ]
