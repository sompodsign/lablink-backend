"""Tests for the email notification service."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.diagnostics.services.notifications import (
    send_report_ready_email,
)


class SendReportReadyEmailTest(SimpleTestCase):
    """Tests for send_report_ready_email function."""

    def _make_mock_report(self):
        """Build a mock Report with the necessary attributes."""
        report = MagicMock()
        report.id = 42
        report.access_token = "abc-123-uuid"
        report.test_type.name = "CBC"
        report.created_at.strftime.return_value = "10 March 2026"

        report.test_order.center.name = "Popular Diagnostic"
        report.test_order.patient.get_full_name.return_value = "Fatima Khan"
        return report

    @patch("apps.diagnostics.services.notifications.send_email")
    def test_sends_email_successfully(self, mock_send_email):
        report = self._make_mock_report()
        mock_send_email.return_value = True

        result = send_report_ready_email(report, "patient@example.com")

        self.assertTrue(result)
        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args
        context = call_kwargs.kwargs.get("context", call_kwargs[1].get("context", {}))
        recipient = call_kwargs.kwargs.get(
            "recipient", call_kwargs[1].get("recipient", "")
        )
        self.assertEqual(context["center_name"], "Popular Diagnostic")
        self.assertEqual(recipient, "patient@example.com")

    @patch("apps.diagnostics.services.notifications.send_email")
    def test_email_body_contains_report_url(self, mock_send_email):
        report = self._make_mock_report()
        mock_send_email.return_value = True

        send_report_ready_email(report, "patient@example.com")

        call_kwargs = mock_send_email.call_args
        context = call_kwargs.kwargs.get("context", call_kwargs[1].get("context", {}))
        # URL now uses a signed token (contains ':') instead of raw UUID
        self.assertIn("/report/", context["report_url"])
        self.assertIn(":", context["report_url"])
        self.assertEqual(context["patient_name"], "Fatima Khan")
        self.assertEqual(context["test_name"], "CBC")

    def test_returns_false_for_empty_email(self):
        report = self._make_mock_report()
        result = send_report_ready_email(report, "")
        self.assertFalse(result)

    def test_returns_false_for_none_email(self):
        report = self._make_mock_report()
        result = send_report_ready_email(report, None)
        self.assertFalse(result)

    @patch("apps.diagnostics.services.notifications.send_email")
    def test_returns_false_on_mail_exception(self, mock_send_email):
        report = self._make_mock_report()
        mock_send_email.side_effect = Exception("SMTP error")

        result = send_report_ready_email(report, "patient@example.com")

        self.assertFalse(result)

    @override_settings(FRONTEND_URL="https://lab.example.com")
    @patch("apps.diagnostics.services.notifications.send_email")
    def test_uses_frontend_url_setting(self, mock_send_email):
        report = self._make_mock_report()
        mock_send_email.return_value = True

        send_report_ready_email(report, "patient@example.com")

        context = mock_send_email.call_args.kwargs.get(
            "context", mock_send_email.call_args[1].get("context", {})
        )
        # URL should use the FRONTEND_URL setting with a signed token
        self.assertTrue(
            context["report_url"].startswith("https://lab.example.com/report/")
        )
