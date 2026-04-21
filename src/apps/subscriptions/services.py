import logging
from datetime import date, timedelta
from decimal import ROUND_UP, Decimal

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import Invoice, Subscription, SubscriptionPlan

from core.tenants.models import DiagnosticCenter

logger = logging.getLogger(__name__)

AI_PLAN_SLUGS = frozenset({"professional", "enterprise"})


def invalidate_subscription_status(center_id: int) -> None:
    cache.delete(f"sub_status:{center_id}")


def get_billing_anchor(subscription: Subscription) -> date:
    if subscription.billing_date:
        return subscription.billing_date
    if subscription.status == Subscription.Status.TRIAL and subscription.trial_end:
        return subscription.trial_end.date()
    return timezone.localdate()


def calculate_downgrade_billing_date(
    *,
    billing_anchor: date | None,
    old_plan_price: Decimal,
    new_plan_price: Decimal,
    today: date | None = None,
) -> date:
    today = today or timezone.localdate()
    anchor = billing_anchor if billing_anchor and billing_anchor > today else today

    if (
        old_plan_price <= 0
        or new_plan_price <= 0
        or new_plan_price >= old_plan_price
    ):
        return anchor

    days_remaining = (anchor - today).days
    if days_remaining <= 0:
        return today

    credited_days = (
        (old_plan_price * Decimal(days_remaining)) / new_plan_price
    ).quantize(Decimal('1'), rounding=ROUND_UP)

    return today + timedelta(days=int(credited_days))


def sync_subscription_ai_state(
    subscription: Subscription, *, reset_credits: bool = False
) -> None:
    center = subscription.center
    should_enable_ai = subscription.plan.slug in AI_PLAN_SLUGS
    center_fields_to_update: list[str] = []

    if center.can_use_ai != should_enable_ai:
        center.can_use_ai = should_enable_ai
        center_fields_to_update.append("can_use_ai")

    if should_enable_ai and not center.use_ai:
        center.use_ai = True
        center_fields_to_update.append("use_ai")

    center_fields_to_update.extend(center.apply_feature_gate_constraints())
    if center_fields_to_update:
        center.save(update_fields=list(dict.fromkeys(center_fields_to_update)))

    if reset_credits:
        monthly_credits = subscription.plan.monthly_ai_credits
        if subscription.available_ai_credits != monthly_credits:
            subscription.available_ai_credits = monthly_credits
            subscription.save(update_fields=["available_ai_credits"])


def _build_invoice_snapshot(subscription: Subscription) -> dict:
    return {
        "status": subscription.status,
        "plan_id": subscription.plan_id,
        "billing_date": (
            subscription.billing_date.isoformat() if subscription.billing_date else None
        ),
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "available_ai_credits": subscription.available_ai_credits,
    }


def _restore_invoice_snapshot(subscription: Subscription, snapshot: dict) -> None:
    billing_date = snapshot.get("billing_date")
    update_fields = ["status", "plan", "billing_date", "cancel_at_period_end"]

    subscription.status = snapshot.get("status", subscription.status)
    plan_id = snapshot.get("plan_id")
    if plan_id:
        subscription.plan_id = plan_id
    subscription.billing_date = (
        date.fromisoformat(billing_date) if billing_date else None
    )
    subscription.cancel_at_period_end = bool(
        snapshot.get("cancel_at_period_end", subscription.cancel_at_period_end)
    )

    if "available_ai_credits" in snapshot:
        subscription.available_ai_credits = snapshot["available_ai_credits"]
        update_fields.append("available_ai_credits")

    subscription.save(update_fields=update_fields)


def _get_next_billing_date(subscription: Subscription, previous_status: str) -> date:
    today = timezone.localdate()

    if previous_status == Subscription.Status.TRIAL:
        anchor = subscription.trial_end.date() if subscription.trial_end else None
        if anchor and anchor > today:
            return anchor + timedelta(days=30)
        return today + timedelta(days=30)

    if not subscription.billing_date or subscription.billing_date <= today:
        return today + timedelta(days=30)
    return subscription.billing_date


@transaction.atomic
def apply_successful_invoice_payment(
    invoice: Invoice,
    *,
    payment_method: str | None = None,
    transaction_id: str | None = None,
    notes: str | None = None,
    gateway_invoice_id: str | None = None,
) -> tuple[Invoice, Subscription]:
    invoice = (
        Invoice.objects.select_for_update()
        .select_related("subscription__center", "subscription__plan")
        .get(pk=invoice.pk)
    )
    subscription = invoice.subscription
    previous_status = subscription.status
    previous_plan_id = subscription.plan_id

    if not invoice.payment_application_snapshot:
        invoice.payment_application_snapshot = _build_invoice_snapshot(subscription)

    invoice.status = Invoice.Status.PAID
    invoice.paid_at = timezone.now()
    if payment_method is not None:
        invoice.payment_method = payment_method
    if transaction_id is not None:
        invoice.transaction_id = transaction_id
    if notes is not None:
        invoice.notes = notes
    if gateway_invoice_id is not None:
        invoice.gateway_invoice_id = gateway_invoice_id
    invoice.save(
        update_fields=[
            "status",
            "paid_at",
            "payment_method",
            "transaction_id",
            "notes",
            "gateway_invoice_id",
            "payment_application_snapshot",
        ]
    )

    update_fields = ["status", "billing_date"]
    if invoice.target_plan_id and subscription.plan_id != invoice.target_plan_id:
        subscription.plan = invoice.target_plan
        update_fields.append("plan")

    subscription.status = Subscription.Status.ACTIVE
    subscription.billing_date = _get_next_billing_date(subscription, previous_status)

    if subscription.cancelled_at is not None:
        subscription.cancelled_at = None
        update_fields.append("cancelled_at")

    if (
        previous_status == Subscription.Status.CANCELLED
        and subscription.cancel_at_period_end
    ):
        subscription.cancel_at_period_end = False
        update_fields.append("cancel_at_period_end")

    subscription.save(update_fields=update_fields)

    reset_ai_credits = (
        previous_status != Subscription.Status.ACTIVE
        or previous_plan_id != subscription.plan_id
    )
    sync_subscription_ai_state(subscription, reset_credits=reset_ai_credits)
    invalidate_subscription_status(subscription.center_id)

    return invoice, subscription


@transaction.atomic
def revert_paid_invoice(invoice: Invoice) -> tuple[Invoice, Subscription]:
    invoice = (
        Invoice.objects.select_for_update()
        .select_related("subscription__center", "subscription__plan")
        .get(pk=invoice.pk)
    )
    subscription = invoice.subscription
    snapshot = invoice.payment_application_snapshot or {}

    invoice.status = Invoice.Status.PENDING
    invoice.paid_at = None
    invoice.payment_application_snapshot = {}
    invoice.save(update_fields=["status", "paid_at", "payment_application_snapshot"])

    if snapshot:
        _restore_invoice_snapshot(subscription, snapshot)
        sync_subscription_ai_state(subscription, reset_credits=False)
    else:
        logger.warning(
            "Invoice %d has no payment_application_snapshot during revert — "
            "re-syncing AI state from current plan.",
            invoice.id,
        )
        sync_subscription_ai_state(subscription, reset_credits=True)

    invalidate_subscription_status(subscription.center_id)
    return invoice, subscription


def reset_subscription_ai_credits(subscription: Subscription) -> None:
    sync_subscription_ai_state(subscription, reset_credits=True)


@transaction.atomic
def apply_credit_to_invoice(invoice: Invoice, center) -> tuple[Invoice, bool]:
    """Apply center's credit_balance to an invoice.

    Returns (invoice, fully_paid).
    If fully_paid is True, the invoice has been marked PAID and the
    subscription activated via ``apply_successful_invoice_payment``.
    """
    invoice = (
        Invoice.objects.select_for_update()
        .select_related("subscription__center", "subscription__plan")
        .get(pk=invoice.pk)
    )
    center = DiagnosticCenter.objects.select_for_update().get(pk=center.pk)
    credit_balance = center.credit_balance or Decimal("0")
    invoice_amount = invoice.amount
    credit_to_apply = min(credit_balance, invoice_amount)

    if credit_to_apply <= 0:
        return invoice, False

    if invoice.original_amount is None:
        invoice.original_amount = invoice_amount

    invoice.credit_applied = credit_to_apply
    remaining = (invoice_amount - credit_to_apply).quantize(Decimal("1"), rounding=ROUND_UP)
    invoice.amount = remaining
    center.credit_balance = credit_balance - credit_to_apply
    center.save(update_fields=["credit_balance"])

    if remaining <= 0:
        invoice.status = Invoice.Status.PAID
        invoice.paid_at = timezone.now()
        invoice.payment_method = Invoice.PaymentMethod.CREDIT
        invoice.save(
            update_fields=[
                "original_amount",
                "amount",
                "credit_applied",
                "status",
                "paid_at",
                "payment_method",
            ],
        )
        invoice, _sub = apply_successful_invoice_payment(
            invoice,
            payment_method=Invoice.PaymentMethod.CREDIT,
        )
        return invoice, True

    invoice.save(
        update_fields=["original_amount", "amount", "credit_applied"],
    )
    return invoice, False
