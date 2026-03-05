import logging
import time

from celery import shared_task

logger = logging.getLogger(__name__)


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
