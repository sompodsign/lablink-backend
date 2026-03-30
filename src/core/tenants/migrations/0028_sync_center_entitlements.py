"""
Data migration: sync can_use_* master switches and available_permissions
for all centers based on their current subscription plan.

Fixes centers where the subscription was created before migration 0027
added the can_use_sms / can_use_email / can_use_ai columns.
"""

from django.db import migrations

NOTIFICATION_PLAN_SLUGS = frozenset({"professional", "enterprise"})
AI_PLAN_SLUGS = frozenset({"professional", "enterprise"})
PREMIUM_PERM_CODENAMES = ("send_sms", "send_email", "use_ai_features")


def sync_entitlements(apps, schema_editor):
    DiagnosticCenter = apps.get_model("tenants", "DiagnosticCenter")
    Subscription = apps.get_model("subscriptions", "Subscription")
    Permission = apps.get_model("tenants", "Permission")

    premium_perms = list(Permission.objects.filter(codename__in=PREMIUM_PERM_CODENAMES))
    all_perms = list(Permission.objects.all())

    for center in DiagnosticCenter.objects.all():
        # ── 1. Sync can_use_* from subscription plan ──────────────
        try:
            sub = (
                Subscription.objects.filter(center=center)
                .order_by("-started_at")
                .first()
            )
        except Exception:
            sub = None

        if sub:
            plan_slug = sub.plan.slug if sub.plan else ""
            should_notify = plan_slug in NOTIFICATION_PLAN_SLUGS
            should_ai = plan_slug in AI_PLAN_SLUGS

            fields = []
            if should_notify and not center.can_use_sms:
                center.can_use_sms = True
                fields.append("can_use_sms")
            if should_notify and not center.can_use_email:
                center.can_use_email = True
                fields.append("can_use_email")
            if should_notify and not center.sms_enabled:
                center.sms_enabled = True
                fields.append("sms_enabled")
            if should_notify and not center.email_notifications_enabled:
                center.email_notifications_enabled = True
                fields.append("email_notifications_enabled")
            if should_ai and not center.can_use_ai:
                center.can_use_ai = True
                fields.append("can_use_ai")

            if fields:
                center.save(update_fields=fields)

        # ── 2. Ensure all perms (including premium) are available ──
        center.available_permissions.set(all_perms)


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0027_add_center_master_switches"),
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(sync_entitlements, migrations.RunPython.noop),
    ]
