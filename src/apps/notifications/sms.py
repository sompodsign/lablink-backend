"""SMS dispatcher using sms.net.bd API.

All SMS notifications go through ``send_sms()`` (synchronous) or
``send_sms_async()`` (Celery task).
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(phone_number: str, message: str) -> bool:
    """Send an SMS via sms.net.bd API.

    Args:
        phone_number: Recipient phone number (with or without country code).
        message: SMS body text.

    Returns:
        ``True`` if the SMS was sent successfully, ``False`` otherwise.
    """
    api_key = getattr(settings, "SMS_API_KEY", "")
    if not api_key:
        logger.warning("SMS_API_KEY not configured, skipping SMS")
        return False

    if not phone_number:
        logger.warning("Empty phone number, skipping SMS")
        return False

    # Normalise: strip spaces/dashes, ensure starts with 880 or 01X
    phone_number = phone_number.strip().replace(" ", "").replace("-", "")

    api_url = getattr(settings, "SMS_API_URL", "https://api.sms.net.bd/sendsms")

    try:
        response = requests.post(
            api_url,
            data={
                "api_key": api_key,
                "msg": message,
                "to": phone_number,
            },
            timeout=15,
        )
        result = response.json()

        if result.get("error") == 0:
            logger.info(
                "SMS sent: %s",
                phone_number,
                extra={"request_id": result.get("data", {}).get("request_id")},
            )
            return True

        logger.error(
            "SMS API error: %s (code %s)",
            result.get("msg", "Unknown"),
            result.get("error"),
            extra={"phone_number": phone_number},
        )
        return False
    except Exception:
        logger.exception("Failed to send SMS to %s", phone_number)
        return False


def send_sms_async(phone_number: str, message: str) -> None:
    """Dispatch SMS via Celery task (non-blocking)."""
    from .tasks import send_sms_task

    send_sms_task.delay(phone_number=phone_number, message=message)
