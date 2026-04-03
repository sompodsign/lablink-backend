"""
Data migration: remove resend_sms and resend_email RBAC permissions.

Resend access is now gated purely by center-level is_sms_active / is_email_active
fields. The HasCenterPermission RBAC guard has been replaced with IsCenterStaff
in the resend_email / resend_sms view actions.
"""

from django.db import migrations

RESEND_CODENAMES = ["resend_sms", "resend_email"]


def remove_resend_permissions(apps, _schema_editor):
    Permission = apps.get_model("tenants", "Permission")
    Permission.objects.filter(codename__in=RESEND_CODENAMES).delete()


def restore_resend_permissions(apps, _schema_editor):
    Permission = apps.get_model("tenants", "Permission")
    DiagnosticCenter = apps.get_model("tenants", "DiagnosticCenter")

    PERMS = [
        ("resend_sms", "Resend Report SMS", "Notifications"),
        ("resend_email", "Resend Report Email", "Notifications"),
    ]
    perm_objs = []
    for codename, name, category in PERMS:
        perm, _ = Permission.objects.get_or_create(
            codename=codename, defaults={"name": name, "category": category}
        )
        perm_objs.append(perm)

    for center in DiagnosticCenter.objects.all():
        center.available_permissions.add(*perm_objs)


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0030_remove_feature_entitlement_permissions"),
    ]

    operations = [
        migrations.RunPython(
            remove_resend_permissions,
            reverse_code=restore_resend_permissions,
        ),
    ]
