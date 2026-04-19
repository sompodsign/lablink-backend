import logging

from celery import shared_task
from django.utils import timezone

from apps.notifications.emails import EmailType, send_email
from apps.subscriptions.services import invalidate_subscription_status

logger = logging.getLogger(__name__)


def _get_center_admin_email(center):
    """Get the best admin email for a center.

    Prefers center.email, falls back to the first staff member's email.
    """
    if center.email:
        return center.email

    from core.tenants.models import Staff

    staff = (
        Staff.objects.filter(center=center)
        .select_related("user")
        .order_by("id")
        .first()
    )
    return staff.user.email if staff and staff.user.email else None


@shared_task(name="subscriptions.check_trial_expirations")
def check_trial_expirations():
    """Daily task: expire trial subscriptions past their trial_end date."""
    from .models import Subscription

    now = timezone.now()
    expiring = Subscription.objects.filter(
        status=Subscription.Status.TRIAL,
        trial_end__lt=now,
    ).select_related("center")

    count = 0
    for sub in expiring:
        sub.status = Subscription.Status.EXPIRED
        sub.save(update_fields=["status"])
        invalidate_subscription_status(sub.center_id)
        count += 1

        admin_email = _get_center_admin_email(sub.center)
        if admin_email:
            send_email(
                EmailType.TRIAL_EXPIRED,
                recipient=admin_email,
                context={"center_name": sub.center.name},
            )

    logger.info("Expired %d trial subscriptions.", count)
    return count


@shared_task(name="subscriptions.send_trial_expiry_warning")
def send_trial_expiry_warning():
    """Daily task: warn centers whose trial ends within 3 days."""
    from .models import Subscription

    now = timezone.now()
    threshold = now + timezone.timedelta(days=3)

    expiring_soon = Subscription.objects.filter(
        status=Subscription.Status.TRIAL,
        trial_end__gt=now,
        trial_end__lte=threshold,
    ).select_related("center")

    for sub in expiring_soon:
        days_left = (sub.trial_end - now).days
        logger.info(
            "Trial expiry warning: %s (%s) — %d days remaining",
            sub.center.name,
            sub.center.domain,
            days_left,
        )

        admin_email = _get_center_admin_email(sub.center)
        if admin_email:
            send_email(
                EmailType.TRIAL_EXPIRY_WARNING,
                recipient=admin_email,
                context={
                    "center_name": sub.center.name,
                    "days_left": days_left,
                },
            )

    return expiring_soon.count()


@shared_task(name="subscriptions.generate_monthly_invoices")
def generate_monthly_invoices():
    """Daily task: generate invoices for active subscriptions whose billing_date is today or past."""
    from dateutil.relativedelta import relativedelta

    from .models import Invoice, Subscription

    today = timezone.now().date()

    subs_due = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
        billing_date__lte=today,
    ).select_related("plan", "center")

    created = 0
    cancelled = 0
    for sub in subs_due:
        if sub.cancel_at_period_end:
            Invoice.objects.filter(
                subscription=sub,
                status__in=[Invoice.Status.PENDING, Invoice.Status.OVERDUE],
            ).update(status=Invoice.Status.CANCELLED)

            sub.status = Subscription.Status.CANCELLED
            sub.cancelled_at = timezone.now()
            sub.save(update_fields=["status", "cancelled_at"])
            invalidate_subscription_status(sub.center_id)

            cancelled += 1
            logger.info(
                "Cancelled subscription for %s (%s) at billing period end.",
                sub.center.name,
                sub.center.domain,
            )
            continue

        existing = Invoice.objects.filter(
            subscription=sub,
            due_date=sub.billing_date,
        ).exists()

        if not existing:
            from decimal import Decimal as D

            credit_to_apply = min(sub.center.credit_balance or D("0.00"), sub.plan.price)
            final_amount = sub.plan.price - credit_to_apply

            invoice = Invoice.objects.create(
                subscription=sub,
                amount=sub.plan.price,
                credit_applied=credit_to_apply,
                due_date=sub.billing_date,
                status=Invoice.Status.PENDING,
            )

            if credit_to_apply > 0:
                sub.center.credit_balance -= credit_to_apply
                sub.center.save(update_fields=["credit_balance"])

            created += 1
            logger.info(
                "Generated invoice for %s (%s) — ৳%s due %s (credit applied: ৳%s, final: ৳%s)",
                sub.center.name,
                sub.center.domain,
                sub.plan.price,
                sub.billing_date,
                credit_to_apply,
                final_amount,
            )

            admin_email = _get_center_admin_email(sub.center)
            if admin_email:
                send_email(
                    EmailType.INVOICE_GENERATED,
                    recipient=admin_email,
                    context={
                        "center_name": sub.center.name,
                        "amount": str(sub.plan.price),
                        "due_date": str(sub.billing_date),
                    },
                )

        sub.billing_date = sub.billing_date + relativedelta(months=1)
        sub.save(update_fields=["billing_date"])

    logger.info(
        "Generated %d new invoices. Cancelled %d subscriptions.", created, cancelled
    )
    return created


@shared_task(name="subscriptions.mark_overdue_invoices")
def mark_overdue_invoices():
    """Daily task: mark pending invoices past their due date as overdue."""
    from .models import Invoice

    today = timezone.now().date()

    overdue_invoices = Invoice.objects.filter(
        status=Invoice.Status.PENDING,
        due_date__lt=today,
    ).select_related("subscription__center")

    count = 0
    for invoice in overdue_invoices:
        invoice.status = Invoice.Status.OVERDUE
        invoice.save(update_fields=["status"])
        count += 1

        center = invoice.subscription.center
        admin_email = _get_center_admin_email(center)
        if admin_email:
            send_email(
                EmailType.INVOICE_OVERDUE,
                recipient=admin_email,
                context={
                    "center_name": center.name,
                    "amount": str(invoice.amount),
                    "due_date": str(invoice.due_date),
                },
            )

    logger.info("Marked %d invoices as overdue.", count)
    return count


GRACE_DAYS_INACTIVE = 7


@shared_task(name="subscriptions.expire_inactive_subscriptions")
def expire_inactive_subscriptions():
    """Daily task: expire INACTIVE subscriptions whose oldest overdue invoice is past grace period.

    Centers with unpaid invoices stay INACTIVE (hard-blocked) for GRACE_DAYS_INACTIVE days.
    After that, their subscription is marked EXPIRED so they get soft-blocked instead
    (can view data but not create/edit). They can still choose a new plan or pay the old one.
    """
    from .models import Invoice, Subscription

    today = timezone.now().date()
    grace_cutoff = today - timezone.timedelta(days=GRACE_DAYS_INACTIVE)

    inactive_subs = Subscription.objects.filter(
        status=Subscription.Status.INACTIVE,
    ).select_related("center")

    expired_count = 0
    for sub in inactive_subs:
        oldest_overdue = (
            Invoice.objects.filter(
                subscription=sub,
                status__in=[
                    Invoice.Status.PENDING,
                    Invoice.Status.OVERDUE,
                ],
            )
            .order_by("due_date")
            .first()
        )

        if not oldest_overdue:
            continue

        if oldest_overdue.due_date < grace_cutoff:
            sub.status = Subscription.Status.EXPIRED
            sub.save(update_fields=["status"])
            invalidate_subscription_status(sub.center_id)

            Invoice.objects.filter(
                subscription=sub,
                status__in=[
                    Invoice.Status.PENDING,
                    Invoice.Status.OVERDUE,
                ],
            ).update(status=Invoice.Status.CANCELLED)

            expired_count += 1
            logger.info(
                "Expired INACTIVE subscription for %s (%s) — no payment in %d days.",
                sub.center.name,
                sub.center.domain,
                GRACE_DAYS_INACTIVE,
            )

            admin_email = _get_center_admin_email(sub.center)
            if admin_email:
                send_email(
EmailType.INACTIVE_EXPIRED,
                    recipient=admin_email,
                    context={
                        "center_name": sub.center.name,
                        "grace_days": GRACE_DAYS_INACTIVE,
                    },
                )

    logger.info("Expired %d inactive subscriptions.", expired_count)
    return expired_count
