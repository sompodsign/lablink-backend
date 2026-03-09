import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.tasks import send_sms_notification

from .models import Report, TestOrder

logger = logging.getLogger(__name__)


@receiver(post_save, sender=TestOrder)
def test_order_created_notification(
    sender, instance: TestOrder, created: bool, **kwargs
) -> None:
    if not created:
        return
    patient = instance.patient
    phone = patient.phone_number or ""
    if not phone:
        logger.info(
            "Skipping SMS: patient has no phone number",
            extra={"test_order_id": instance.id, "patient_id": patient.id},
        )
        return
    message = (
        f"A {instance.test_type.name} test has been ordered for you "
        f"at {instance.center.name}. Please visit us at your scheduled time."
    )
    send_sms_notification.delay(phone, message)


@receiver(post_save, sender=Report)
def report_ready_notification(
    sender, instance: Report, created: bool, **kwargs
) -> None:
    if not created:
        return
    patient = instance.test_order.patient
    phone = patient.phone_number or ""
    if not phone:
        logger.info(
            "Skipping SMS: patient has no phone number",
            extra={"report_id": instance.id, "patient_id": patient.id},
        )
        return
    center_name = instance.test_order.center.name
    message = (
        f"Your {instance.test_type.name} report is ready. "
        f"Please visit {center_name} to collect it, "
        f"or check your online portal."
    )
    send_sms_notification.delay(phone, message)
