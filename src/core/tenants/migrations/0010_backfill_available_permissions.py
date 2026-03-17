"""
Data migration: backfill available_permissions for all existing centers
and add `manage_roles` permission to seeded data.
"""

from django.db import migrations


def backfill_available_permissions(apps, schema_editor):
    """Give all existing centers access to ALL existing permissions."""
    DiagnosticCenter = apps.get_model("tenants", "DiagnosticCenter")
    Permission = apps.get_model("tenants", "Permission")

    all_perms = Permission.objects.all()
    for center in DiagnosticCenter.objects.all():
        center.available_permissions.set(all_perms)


def add_manage_roles_permission(apps, schema_editor):
    """Add 'manage_roles' permission and assign it to Admin roles."""
    Permission = apps.get_model("tenants", "Permission")
    Role = apps.get_model("tenants", "Role")

    perm, _created = Permission.objects.get_or_create(
        codename="manage_roles",
        defaults={
            "name": "Manage Roles",
            "category": "Administration",
            "is_custom": False,
        },
    )

    # Add to all Admin roles and all center available_permissions
    for role in Role.objects.filter(name="Admin"):
        role.permissions.add(perm)

    DiagnosticCenter = apps.get_model("tenants", "DiagnosticCenter")
    for center in DiagnosticCenter.objects.all():
        center.available_permissions.add(perm)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0009_superadmin_permission_management"),
    ]

    operations = [
        migrations.RunPython(
            backfill_available_permissions,
            reverse_code=noop,
        ),
        migrations.RunPython(
            add_manage_roles_permission,
            reverse_code=noop,
        ),
    ]
