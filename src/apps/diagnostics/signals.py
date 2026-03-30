import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.sms import send_sms_async
from core.tenants.models import DiagnosticCenter

from .models import ReportTemplate, TestOrder, TestType

logger = logging.getLogger(__name__)


@receiver(post_save, sender=TestOrder)
def test_order_created_notification(
    sender, instance: TestOrder, created: bool, **kwargs
) -> None:
    if not created:
        return

    center = instance.center
    if not center.is_sms_active:
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
        f"{center.name}\n"
        f"\n"
        f"Dear {patient.get_full_name()},\n"
        f"A {instance.test_type.name} test has been ordered for you.\n"
        f"\n"
        f"Please visit us at your scheduled time.\n"
        f"Thank you for choosing {center.name}."
    )
    send_sms_async(phone, message)


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
            "Created %d report templates for center %s",
            len(templates_to_create),
            instance.name,
        )
