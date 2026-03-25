from django.db import migrations


def backfill_resend_permissions(apps, schema_editor):
    Role = apps.get_model("tenants", "Role")
    Permission = apps.get_model("tenants", "Permission")

    resend_perms = list(
        Permission.objects.filter(codename__in=["resend_email", "resend_sms"])
    )
    if not resend_perms:
        return

    roles = Role.objects.filter(
        name__in=["Admin", "Medical Technologist", "Receptionist"]
    )

    for role in roles:
        # Check if the center actually has the 'resend_email' available
        # by checking available_permissions. (We need to query it from the many-to-many field)
        center = role.center
        available_ids = set(center.available_permissions.values_list("id", flat=True))

        # We only add the perms if they are available to the center
        valid_perms_to_add = [p for p in resend_perms if p.id in available_ids]
        if valid_perms_to_add:
            role.permissions.add(*valid_perms_to_add)


def reverse_backfill(apps, schema_editor):
    pass  # No need to reverse since removing permissions specifically from these roles might remove them entirely


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0022_add_resend_permissions"),
    ]

    operations = [
        migrations.RunPython(backfill_resend_permissions, reverse_backfill),
    ]
