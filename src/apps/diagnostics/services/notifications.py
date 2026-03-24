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


def send_batch_report_ready_email(reports, patient_email: str) -> bool:
    """Send a single grouped email listing all completed reports.

    Falls back to send_report_ready_email when there is only one report.

    Args:
        reports: Iterable of Report instances (must all belong to same patient).
        patient_email: Patient's email address.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    if not patient_email:
        return False

    reports_list = list(reports)
    if not reports_list:
        return False

    if len(reports_list) == 1:
        return send_report_ready_email(reports_list[0], patient_email)

    first_report = reports_list[0]
    center = first_report.test_order.center
    patient = first_report.test_order.patient

    base_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")

    # Build a signed URL for each report so the patient can access all of them
    report_links = "\n".join(
        f"  • {r.test_type.name}: {base_url}/report/{make_report_token(r)}"
        for r in reports_list
    )
    test_names = ", ".join(r.test_type.name for r in reports_list)

    try:
        return send_email(
            EmailType.BATCH_REPORT_READY,
            recipient=patient_email,
            context={
                "patient_name": patient.get_full_name(),
                "test_names": test_names,
                "report_links": report_links,
                "report_date": first_report.created_at.strftime("%d %B %Y"),
                "center_name": center.name,
            },
        )
    except Exception:
        logger.exception("Failed to send batch report-ready email to %s", patient_email)
        return False
