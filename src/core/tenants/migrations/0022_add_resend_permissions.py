"""
Data migration: add "resend_email" and "resend_sms" permissions.
- Creates the two new Permission rows
- Grants them to Admin (all perms), Medical Technologist, and Receptionist roles
- Adds them to every center's available_permissions
"""

from django.db import migrations

NEW_PERMISSIONS = [
    ("resend_email", "Resend Report Email", "Notifications"),
    ("resend_sms", "Resend Report SMS", "Notifications"),
]

# Roles that should get these permissions by default
ROLES_WITH_RESEND = ["Admin", "Medical Technologist", "Receptionist"]


def add_resend_permissions(apps, _schema_editor):
    Permission = apps.get_model("tenants", "Permission")
    Role = apps.get_model("tenants", "Role")
    DiagnosticCenter = apps.get_model("tenants", "DiagnosticCenter")

    # Create permission rows
    perm_objs = []
    for codename, name, category in NEW_PERMISSIONS:
        perm, _ = Permission.objects.get_or_create(
            codename=codename,
            defaults={"name": name, "category": category},
        )
        perm_objs.append(perm)

    # Grant to specified roles across all centers
    for role in Role.objects.filter(name__in=ROLES_WITH_RESEND):
        role.permissions.add(*perm_objs)

    # Admin roles get all permissions — also ensure they have these
    for role in Role.objects.filter(name="Admin"):
        role.permissions.add(*perm_objs)

    # Add to every center's available_permissions
    for center in DiagnosticCenter.objects.all():
        center.available_permissions.add(*perm_objs)


def remove_resend_permissions(apps, _schema_editor):
    Permission = apps.get_model("tenants", "Permission")
    Permission.objects.filter(
        codename__in=["resend_email", "resend_sms"],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0021_add_medical_assistant_role"),
    ]

    operations = [
        migrations.RunPython(
            add_resend_permissions,
            reverse_code=remove_resend_permissions,
        ),
    ]
