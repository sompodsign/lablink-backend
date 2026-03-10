import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.tasks import send_sms_notification
from core.tenants.models import DiagnosticCenter

from .models import Report, ReportTemplate, TestOrder, TestType

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


@receiver(post_save, sender=DiagnosticCenter)
def create_report_templates_for_new_center(
    sender, instance: DiagnosticCenter, created: bool, **kwargs
) -> None:
    """Auto-create report templates for every TestType when a new center is created."""
    if not created:
        return

    # Import seed data lazily to avoid circular imports
    from apps.diagnostics.template_fields import TEMPLATE_FIELDS

    test_types = TestType.objects.all()
    templates_to_create = []
    for test_type in test_types:
        fields = TEMPLATE_FIELDS.get(test_type.name)
        if fields:
            templates_to_create.append(
                ReportTemplate(
                    center=instance,
                    test_type=test_type,
                    fields=fields,
                )
            )
    if templates_to_create:
        ReportTemplate.objects.bulk_create(templates_to_create, ignore_conflicts=True)
        logger.info(
            'Created %d report templates for center %s',
            len(templates_to_create),
            instance.name,
        )
