import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Subscription

logger = logging.getLogger(__name__)

# Plan slugs that include SMS/Email notifications
NOTIFICATION_PLAN_SLUGS = frozenset({"professional", "enterprise"})

# Plan slugs that include AI features
AI_PLAN_SLUGS = frozenset({"professional", "enterprise"})


@receiver(post_save, sender=Subscription)
def sync_center_notification_flags(sender, instance: Subscription, **kwargs) -> None:
    """Auto-enable/disable notification flags based on subscription plan.

    Only runs on subscription CREATION to set initial entitlements.
    Subsequent changes are managed manually by the Superadmin via the
    center edit UI, so we never override their manual toggles.
    Syncs AI entitlements and credits based on plan.
    """
    created = kwargs.get("created", False)
    center = instance.center
    plan_slug = instance.plan.slug
    should_enable_notifications = plan_slug in NOTIFICATION_PLAN_SLUGS
    should_enable_ai = plan_slug in AI_PLAN_SLUGS

    # ── Only sync entitlement flags on creation ───────────────────
    if created:
        fields_to_update: list[str] = []

        if center.can_use_sms != should_enable_notifications:
            center.can_use_sms = should_enable_notifications
            fields_to_update.append("can_use_sms")

        if center.can_use_email != should_enable_notifications:
            center.can_use_email = should_enable_notifications
            fields_to_update.append("can_use_email")

        if center.can_use_ai != should_enable_ai:
            center.can_use_ai = should_enable_ai
            fields_to_update.append("can_use_ai")

        fields_to_update.extend(center.apply_feature_gate_constraints())

        if fields_to_update:
            center.save(update_fields=list(dict.fromkeys(fields_to_update)))

        # ── Sync AI credits ────────────────────────────────────────
        monthly_credits = instance.plan.monthly_ai_credits
        if instance.available_ai_credits != monthly_credits:
            instance.available_ai_credits = monthly_credits
            instance.save(update_fields=["available_ai_credits"])

    logger.info(
        "Center %s flags updated: sms=%s, email=%s, ai=%s, ai_credits=%d (plan=%s)",
        center.name,
        center.is_sms_active,
        center.is_email_active,
        center.is_ai_active,
        instance.available_ai_credits,
        plan_slug,
    )
