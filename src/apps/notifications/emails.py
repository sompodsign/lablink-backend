"""Centralized email dispatcher.

All transactional emails go through ``send_email()`` (synchronous) or
``send_email_async()`` (Celery task).
"""

import logging
from enum import StrEnum

from django.conf import settings
from django.core.mail import send_mail

from .templates import TEMPLATES

logger = logging.getLogger(__name__)


class EmailType(StrEnum):
    """Every transactional email the platform can send."""

    # Auth & Account
    WELCOME_PATIENT = 'welcome_patient'
    PASSWORD_RESET = 'password_reset'
    PASSWORD_RESET_SUCCESS = 'password_reset_success'
    ACCOUNT_APPROVED = 'account_approved'
    ACCOUNT_DECLINED = 'account_declined'

    # Appointments
    APPOINTMENT_BOOKED = 'appointment_booked'
    APPOINTMENT_CONFIRMED = 'appointment_confirmed'
    APPOINTMENT_CANCELLED = 'appointment_cancelled'

    # Reports
    REPORT_READY = 'report_ready'

    # Staff & Doctor Credentials
    STAFF_CREDENTIALS = 'staff_credentials'
    DOCTOR_CREDENTIALS = 'doctor_credentials'

    # Subscriptions & Billing
    TRIAL_EXPIRY_WARNING = 'trial_expiry_warning'
    TRIAL_EXPIRED = 'trial_expired'
    INVOICE_GENERATED = 'invoice_generated'
    INVOICE_OVERDUE = 'invoice_overdue'
    PAYMENT_RECEIVED = 'payment_received'

    # Admin Operations
    CENTER_CREATED = 'center_created'
    CENTER_DEACTIVATED = 'center_deactivated'


def send_email(
    email_type: EmailType | str,
    recipient: str,
    context: dict,
    from_email: str | None = None,
) -> bool:
    """Render a template and send an email synchronously.

    Args:
        email_type: Key from ``EmailType`` enum.
        recipient: Email address of the recipient.
        context: Dict of values to format into the template.
        from_email: Override the default ``DEFAULT_FROM_EMAIL``.

    Returns:
        ``True`` if the email was sent successfully, ``False`` otherwise.
    """
    template = TEMPLATES.get(str(email_type))
    if not template:
        logger.error('Unknown email type: %s', email_type)
        return False

    if not recipient:
        logger.warning('Empty recipient for email type: %s', email_type)
        return False

    subject_tpl, body_tpl = template

    try:
        subject = subject_tpl.format(**context)
        body = body_tpl.format(**context)
    except KeyError:
        logger.exception(
            'Missing context key for email type %s',
            email_type,
            extra={'context_keys': list(context.keys())},
        )
        return False

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        logger.info(
            'Email sent: %s → %s',
            email_type,
            recipient,
        )
        return True
    except Exception:
        logger.exception(
            'Failed to send email: %s → %s',
            email_type,
            recipient,
        )
        return False


def send_email_async(
    email_type: EmailType | str,
    recipient: str,
    context: dict,
    from_email: str | None = None,
) -> None:
    """Dispatch email via Celery task (non-blocking).

    Use this for emails that don't need to block the request/response cycle.
    """
    from .tasks import send_email_task

    send_email_task.delay(
        email_type=str(email_type),
        recipient=recipient,
        context=context,
        from_email=from_email,
    )
