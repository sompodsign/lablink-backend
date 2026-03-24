import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="notifications.send_email")
def send_email_task(
    email_type: str,
    recipient: str,
    context: dict,
    from_email: str | None = None,
) -> bool:
    """Celery task: render template and send email."""
    from .emails import send_email

    return send_email(
        email_type=email_type,
        recipient=recipient,
        context=context,
        from_email=from_email,
    )


@shared_task(name="notifications.send_sms")
def send_sms_task(phone_number: str, message: str) -> bool:
    """Celery task: send SMS via sms.net.bd API."""
    from .sms import send_sms

    return send_sms(phone_number=phone_number, message=message)
