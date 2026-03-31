"""
Data migration: remove Feature Entitlement and Notification RBAC permissions.

- send_sms / send_email / use_ai_features: duplicated DiagnosticCenter boolean
  fields (can_use_*). Removed in favour of the superadmin center-level gates.
- resend_sms / resend_email: previously used to allow per-role resend control,
  but the same gating is now handled purely by center-level is_sms_active /
  is_email_active. Resend endpoints now require IsCenterStaff only.
"""

from django.db import migrations

CODENAMES_TO_REMOVE = [
    'send_sms',
    'send_email',
    'use_ai_features',
    'resend_sms',
    'resend_email',
]


def remove_permissions(apps, _schema_editor):
    Permission = apps.get_model('tenants', 'Permission')
    # Django automatically removes M2M through-table rows when the target is deleted
    Permission.objects.filter(codename__in=CODENAMES_TO_REMOVE).delete()


def restore_permissions(apps, _schema_editor):
    """Reverse: re-create all five permissions."""
    Permission = apps.get_model('tenants', 'Permission')
    Role = apps.get_model('tenants', 'Role')
    DiagnosticCenter = apps.get_model('tenants', 'DiagnosticCenter')

    PERMS = [
        ('send_sms', 'Global SMS Capability', 'Feature Entitlements'),
        ('send_email', 'Global Email Capability', 'Feature Entitlements'),
        ('use_ai_features', 'Use AI Features (Report Extraction, Chatbot)', 'Feature Entitlements'),
        ('resend_sms', 'Resend Report SMS', 'Notifications'),
        ('resend_email', 'Resend Report Email', 'Notifications'),
    ]
    perm_objs = []
    for codename, name, category in PERMS:
        perm, _ = Permission.objects.get_or_create(
            codename=codename, defaults={'name': name, 'category': category}
        )
        perm_objs.append(perm)

    for center in DiagnosticCenter.objects.all():
        center.available_permissions.add(*perm_objs)


class Migration(migrations.Migration):
    dependencies = [
        ('tenants', '0029_add_center_admin_toggles'),
    ]

    operations = [
        migrations.RunPython(
            remove_permissions,
            reverse_code=restore_permissions,
        ),
    ]
