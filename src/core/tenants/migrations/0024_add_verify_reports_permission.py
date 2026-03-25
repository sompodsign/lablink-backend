from django.db import migrations


def create_and_backfill_verify_permission(apps, schema_editor):
    Permission = apps.get_model("tenants", "Permission")
    Role = apps.get_model("tenants", "Role")
    DiagnosticCenter = apps.get_model("tenants", "DiagnosticCenter")

    perm, _ = Permission.objects.get_or_create(
        codename="verify_reports",
        defaults={
            "name": "Verify Reports",
            "category": "Reports",
            "is_custom": False,
        },
    )

    # Make it available to all centers
    for center in DiagnosticCenter.objects.all():
        center.available_permissions.add(perm)

    # Grant it to existing Admin and Medical Technologist roles
    roles = Role.objects.filter(name__in=["Admin", "Medical Technologist"])
    for role in roles:
        role.permissions.add(perm)


def reverse_func(apps, schema_editor):
    Permission = apps.get_model("tenants", "Permission")
    Permission.objects.filter(codename="verify_reports").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0023_backfill_resend_permissions"),
    ]

    operations = [
        migrations.RunPython(create_and_backfill_verify_permission, reverse_func),
    ]
