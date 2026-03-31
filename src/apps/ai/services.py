import logging

from django.db import transaction

from apps.ai.models import AICreditUsageLog
from apps.subscriptions.models import Subscription

logger = logging.getLogger(__name__)


class InsufficientAICreditsError(Exception):
    """Raised when a center has no remaining AI credits."""


class AIFeatureDisabledError(Exception):
    """Raised when AI is not enabled for a center."""


def check_ai_access(center) -> Subscription:
    """Verify the center has AI enabled and credits remaining.

    Returns the active subscription if access is granted.
    Raises AIFeatureDisabledError or InsufficientAICreditsError otherwise.
    """
    if not center.is_ai_active:
        raise AIFeatureDisabledError(
            'AI features are not enabled for this center. '
            'Contact your administrator to activate them.'
        )

    try:
        subscription = Subscription.objects.select_related("plan").get(
            center=center,
            status__in=[
                Subscription.Status.ACTIVE,
                Subscription.Status.TRIAL,
            ],
        )
    except Subscription.DoesNotExist as err:
        raise AIFeatureDisabledError(
            "No active subscription found. "
            "Please activate a subscription to use AI features."
        ) from err

    if subscription.available_ai_credits <= 0:
        raise InsufficientAICreditsError(
            "No AI credits remaining. Please upgrade your plan or purchase a top-up."
        )

    return subscription


def deduct_ai_credit(
    *,
    center,
    task_type: str,
    performed_by=None,
    credits: int = 1,
    input_tokens: int = 0,
    output_tokens: int = 0,
    metadata: dict | None = None,
) -> AICreditUsageLog:
    """Atomically deduct AI credits and log the usage.

    This is the single, central function that ALL AI features
    must call after a successful AI API response.
    """
    with transaction.atomic():
        subscription = (
            Subscription.objects.select_for_update()
            .filter(
                center=center,
                status__in=[
                    Subscription.Status.ACTIVE,
                    Subscription.Status.TRIAL,
                ],
            )
            .first()
        )

        if not subscription or subscription.available_ai_credits < credits:
            raise InsufficientAICreditsError(
                "Not enough AI credits to complete this operation."
            )

        subscription.available_ai_credits -= credits
        subscription.save(update_fields=["available_ai_credits"])

        log = AICreditUsageLog.objects.create(
            center=center,
            task_type=task_type,
            credits_used=credits,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            performed_by=performed_by,
            metadata=metadata or {},
        )

    logger.info(
        "AI credit deducted: center=%s, task=%s, remaining=%d",
        center.name,
        task_type,
        subscription.available_ai_credits,
    )

    return log
