"""Email notification service for report delivery."""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

REPORT_READY_SUBJECT = 'Your Lab Report is Ready — {center_name}'

REPORT_READY_BODY = """Dear {patient_name},

Your lab report for {test_name} is ready.

You can view your report online at:
{report_url}

Report Details:
- Test: {test_name}
- Date: {report_date}
- Center: {center_name}

This is an automated message from {center_name}.
Please contact us if you have any questions.
"""


def send_report_ready_email(report, patient_email: str) -> bool:
    """Send report-ready notification email to patient.

    Args:
        report: Report instance
        patient_email: Patient's email address

    Returns:
        True if email was sent successfully, False otherwise.
    """
    if not patient_email:
        return False

    center = report.test_order.center
    patient = report.test_order.patient

    # Build the report URL
    base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    report_url = f'{base_url}/report/{report.access_token}'

    context = {
        'patient_name': patient.get_full_name(),
        'test_name': report.test_type.name,
        'report_date': report.created_at.strftime('%d %B %Y'),
        'center_name': center.name,
        'report_url': report_url,
    }

    subject = REPORT_READY_SUBJECT.format(**context)
    body = REPORT_READY_BODY.format(**context)

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient_email],
            fail_silently=False,
        )
        logger.info(
            'Report ready email sent',
            extra={
                'report_id': report.id,
                'patient_email': patient_email,
            },
        )
        return True
    except Exception:
        logger.exception(
            'Failed to send report ready email',
            extra={
                'report_id': report.id,
                'patient_email': patient_email,
            },
        )
        return False
