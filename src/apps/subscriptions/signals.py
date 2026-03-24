import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Subscription

logger = logging.getLogger(__name__)

# Plan slugs that include SMS/Email notifications
NOTIFICATION_PLAN_SLUGS = frozenset({"professional", "enterprise"})


@receiver(post_save, sender=Subscription)
def sync_center_notification_flags(sender, instance: Subscription, **kwargs) -> None:
    """Auto-enable/disable notification flags based on subscription plan.

    Professional and Enterprise plans get SMS and email enabled.
    Lower-tier plans get them disabled (unless superadmin overrides manually).
    """
    center = instance.center
    plan_slug = instance.plan.slug
    should_enable = plan_slug in NOTIFICATION_PLAN_SLUGS

    fields_to_update: list[str] = []

    if center.sms_enabled != should_enable:
        center.sms_enabled = should_enable
        fields_to_update.append("sms_enabled")

    if center.email_notifications_enabled != should_enable:
        center.email_notifications_enabled = should_enable
        fields_to_update.append("email_notifications_enabled")

    if fields_to_update:
        center.save(update_fields=fields_to_update)
        logger.info(
            "Center %s notification flags updated: sms=%s, email=%s (plan=%s)",
            center.name,
            center.sms_enabled,
            center.email_notifications_enabled,
            plan_slug,
        )
