import logging
import time

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='notifications.send_email')
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


@shared_task
def send_sms_notification(phone_number: str, message: str) -> str:
    logger.info(
        'Sending SMS notification',
        extra={'phone_number': phone_number, 'message': message[:100]},
    )
    # TODO: Replace with real SMS provider integration (e.g., Twilio, bKash SMS)
    time.sleep(1)  # Simulate network delay
    logger.info('SMS sent', extra={'phone_number': phone_number})
    return f'SMS sent to {phone_number}'
