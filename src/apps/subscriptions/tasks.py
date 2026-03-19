import logging

from celery import shared_task
from django.utils import timezone

from apps.notifications.emails import EmailType, send_email

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
        .select_related('user')
        .order_by('id')
        .first()
    )
    return staff.user.email if staff and staff.user.email else None


@shared_task(name='subscriptions.check_trial_expirations')
def check_trial_expirations():
    """Daily task: expire trial subscriptions past their trial_end date."""
    from .models import Subscription

    now = timezone.now()
    expiring = Subscription.objects.filter(
        status=Subscription.Status.TRIAL,
        trial_end__lt=now,
    ).select_related('center')

    count = 0
    for sub in expiring:
        sub.status = Subscription.Status.EXPIRED
        sub.save(update_fields=['status'])
        count += 1

        admin_email = _get_center_admin_email(sub.center)
        if admin_email:
            send_email(
                EmailType.TRIAL_EXPIRED,
                recipient=admin_email,
                context={'center_name': sub.center.name},
            )

    logger.info('Expired %d trial subscriptions.', count)
    return count


@shared_task(name='subscriptions.send_trial_expiry_warning')
def send_trial_expiry_warning():
    """Daily task: warn centers whose trial ends within 3 days."""
    from .models import Subscription

    now = timezone.now()
    threshold = now + timezone.timedelta(days=3)

    expiring_soon = Subscription.objects.filter(
        status=Subscription.Status.TRIAL,
        trial_end__gt=now,
        trial_end__lte=threshold,
    ).select_related('center')

    for sub in expiring_soon:
        days_left = (sub.trial_end - now).days
        logger.info(
            'Trial expiry warning: %s (%s) — %d days remaining',
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
                    'center_name': sub.center.name,
                    'days_left': days_left,
                },
            )

    return expiring_soon.count()


@shared_task(name='subscriptions.generate_monthly_invoices')
def generate_monthly_invoices():
    """Daily task: generate invoices for active subscriptions whose billing_date is today or past."""
    from datetime import timedelta

    from .models import Invoice, Subscription

    today = timezone.now().date()

    subs_due = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
        billing_date__lte=today,
    ).select_related('plan', 'center')

    created = 0
    for sub in subs_due:
        # Check if an invoice already exists for this billing cycle
        existing = Invoice.objects.filter(
            subscription=sub,
            due_date=sub.billing_date,
        ).exists()

        if not existing:
            Invoice.objects.create(
                subscription=sub,
                amount=sub.plan.price,
                due_date=sub.billing_date,
                status=Invoice.Status.PENDING,
            )
            created += 1
            logger.info(
                'Generated invoice for %s (%s) — ৳%s due %s',
                sub.center.name,
                sub.center.domain,
                sub.plan.price,
                sub.billing_date,
            )

            admin_email = _get_center_admin_email(sub.center)
            if admin_email:
                send_email(
                    EmailType.INVOICE_GENERATED,
                    recipient=admin_email,
                    context={
                        'center_name': sub.center.name,
                        'amount': str(sub.plan.price),
                        'due_date': str(sub.billing_date),
                    },
                )

        # Advance billing_date to next month
        sub.billing_date = sub.billing_date + timedelta(days=30)
        sub.save(update_fields=['billing_date'])

    logger.info('Generated %d new invoices.', created)
    return created


@shared_task(name='subscriptions.mark_overdue_invoices')
def mark_overdue_invoices():
    """Daily task: mark pending invoices past their due date as overdue."""
    from .models import Invoice

    today = timezone.now().date()

    overdue_invoices = Invoice.objects.filter(
        status=Invoice.Status.PENDING,
        due_date__lt=today,
    ).select_related('subscription__center')

    count = 0
    for invoice in overdue_invoices:
        invoice.status = Invoice.Status.OVERDUE
        invoice.save(update_fields=['status'])
        count += 1

        center = invoice.subscription.center
        admin_email = _get_center_admin_email(center)
        if admin_email:
            send_email(
                EmailType.INVOICE_OVERDUE,
                recipient=admin_email,
                context={
                    'center_name': center.name,
                    'amount': str(invoice.amount),
                    'due_date': str(invoice.due_date),
                },
            )

    logger.info('Marked %d invoices as overdue.', count)
    return count
