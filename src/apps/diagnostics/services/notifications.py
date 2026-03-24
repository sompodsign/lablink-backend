"""Email notification service for report delivery."""

import logging

from django.conf import settings

from apps.diagnostics.tokens import make_report_token
from apps.notifications.emails import EmailType, send_email

logger = logging.getLogger(__name__)


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

    # Build a signed, expiring report URL (30-day token)
    signed_token = make_report_token(report)
    base_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    report_url = f"{base_url}/report/{signed_token}"

    try:
        return send_email(
            EmailType.REPORT_READY,
            recipient=patient_email,
            context={
                "patient_name": patient.get_full_name(),
                "test_name": report.test_type.name,
                "report_date": report.created_at.strftime("%d %B %Y"),
                "center_name": center.name,
                "report_url": report_url,
            },
        )
    except Exception:
        logger.exception("Failed to send report-ready email to %s", patient_email)
        return False
