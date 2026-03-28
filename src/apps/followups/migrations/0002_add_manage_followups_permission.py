"""
Data migration: add 'manage_followups' permission and assign it to Admin roles.
"""

from django.db import migrations


def add_manage_followups_permission(apps, schema_editor):
    Permission = apps.get_model("tenants", "Permission")
    Role = apps.get_model("tenants", "Role")
    DiagnosticCenter = apps.get_model("tenants", "DiagnosticCenter")

    perm, _created = Permission.objects.get_or_create(
        codename="manage_followups",
        defaults={
            "name": "Manage Follow-Ups",
            "category": "Patient Care",
            "is_custom": False,
        },
    )

    # Grant to all Admin roles
    for role in Role.objects.filter(name="Admin"):
        role.permissions.add(perm)

    # Add to all center available_permissions so it's assignable
    for center in DiagnosticCenter.objects.all():
        center.available_permissions.add(perm)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0024_add_verify_reports_permission"),
        ("followups", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            add_manage_followups_permission,
            reverse_code=noop,
        ),
    ]
