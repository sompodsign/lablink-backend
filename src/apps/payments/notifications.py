import logging

from apps.notifications.tasks import send_email_task, send_sms_task

from .models import Invoice

logger = logging.getLogger(__name__)


def get_patient_name(invoice: Invoice) -> str:
    if invoice.patient:
        return invoice.patient.get_full_name() or invoice.patient.email
    return invoice.walk_in_name or "Walk-in"


def get_patient_phone(invoice: Invoice) -> str:
    if invoice.patient:
        return getattr(invoice.patient, "phone_number", "") or ""
    return invoice.walk_in_phone or ""


def get_patient_email(invoice: Invoice) -> str:
    if invoice.patient:
        return getattr(invoice.patient, "email", "") or ""
    # Walk-in patients don't have emails stored at the invoice level currently
    return ""


def send_invoice_created_sms(invoice: Invoice) -> bool:
    phone_number = get_patient_phone(invoice)
    if not phone_number:
        logger.warning(
            f"Skipping SMS invoice for {invoice.invoice_number} - No phone number"
        )
        return False

    amount = (
        int(invoice.total) if invoice.total == int(invoice.total) else invoice.total
    )
    message = (
        f"LabLink: Invoice {invoice.invoice_number} created for {get_patient_name(invoice)}. "
        f"Total: {amount} BDT. Thank you for choosing {invoice.center.name}."
    )
    send_sms_task.delay(phone_number, message)
    logger.info(f"Queued SMS invoice for {invoice.invoice_number}")
    return True


def send_invoice_created_email(invoice: Invoice) -> bool:
    email_address = get_patient_email(invoice)
    if not email_address:
        logger.warning(
            f"Skipping Email invoice for {invoice.invoice_number} - No email address"
        )
        return False

    amount = (
        int(invoice.total) if invoice.total == int(invoice.total) else invoice.total
    )
    subject = f"Invoice {invoice.invoice_number} from {invoice.center.name}"
    body = (
        f"Dear {get_patient_name(invoice)},\n\n"
        f"Your invoice {invoice.invoice_number} has been created.\n"
        f"Total Amount: {amount} BDT\n\n"
        f"Thank you,\n{invoice.center.name}"
    )
    send_email_task.delay(
        email_address,
        subject,
        body,
    )
    logger.info(f"Queued Email invoice for {invoice.invoice_number}")
    return True
