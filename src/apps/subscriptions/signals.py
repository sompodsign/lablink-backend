import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Subscription

logger = logging.getLogger(__name__)

# Plan slugs that include SMS/Email notifications
NOTIFICATION_PLAN_SLUGS = frozenset({"professional", "enterprise"})

# Plan slugs that include AI features
AI_PLAN_SLUGS = frozenset({"professional", "enterprise"})

# Permissions granted only for notification-tier plans
NOTIFICATION_PERMS = ("resend_email", "resend_sms")

# Roles that should receive notification permissions
NOTIFICATION_ROLES = ("Admin", "Medical Technologist", "Receptionist")


@receiver(post_save, sender=Subscription)
def sync_center_notification_flags(sender, instance: Subscription, **kwargs) -> None:
    """Auto-enable/disable notification flags based on subscription plan.

    Professional and Enterprise plans get SMS and email enabled.
    Lower-tier plans get them disabled (unless superadmin overrides manually).
    Also grants/revokes resend_email and resend_sms permissions on roles.
    Syncs AI entitlements and credits based on plan.
    """
    from core.tenants.models import Permission, Role

    center = instance.center
    plan_slug = instance.plan.slug
    should_enable_notifications = plan_slug in NOTIFICATION_PLAN_SLUGS
    should_enable_ai = plan_slug in AI_PLAN_SLUGS

    fields_to_update: list[str] = []

    if center.can_use_sms != should_enable_notifications:
        center.can_use_sms = should_enable_notifications
        fields_to_update.append("can_use_sms")

    if center.can_use_email != should_enable_notifications:
        center.can_use_email = should_enable_notifications
        fields_to_update.append("can_use_email")

    # ── AI entitlement ────────────────────────────────────────────
    if center.can_use_ai != should_enable_ai:
        center.can_use_ai = should_enable_ai
        fields_to_update.append("can_use_ai")

    if fields_to_update:
        center.save(update_fields=fields_to_update)

    # ── Sync AI credits only on creation ────────────────────────────
    created = kwargs.get("created", False)
    if created:
        monthly_credits = instance.plan.monthly_ai_credits
        if instance.available_ai_credits != monthly_credits:
            instance.available_ai_credits = monthly_credits
            instance.save(update_fields=["available_ai_credits"])

    # ── Sync resend permissions on center roles ───────────────────
    perms = list(Permission.objects.filter(codename__in=NOTIFICATION_PERMS))
    if perms:
        roles = Role.objects.filter(center=center, name__in=NOTIFICATION_ROLES)
        for role in roles:
            if should_enable_notifications:
                role.permissions.add(*perms)
            else:
                role.permissions.remove(*perms)

    logger.info(
        "Center %s flags updated: sms=%s, email=%s, ai=%s, ai_credits=%d (plan=%s)",
        center.name,
        center.sms_enabled,
        center.email_notifications_enabled,
        center.can_use_ai,
        instance.available_ai_credits,
        plan_slug,
    )
