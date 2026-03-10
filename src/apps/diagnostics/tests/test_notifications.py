"""Tests for the email notification service."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.diagnostics.services.notifications import (
    REPORT_READY_BODY,
    send_report_ready_email,
)


class SendReportReadyEmailTest(SimpleTestCase):
    """Tests for send_report_ready_email function."""

    def _make_mock_report(self):
        """Build a mock Report with the necessary attributes."""
        report = MagicMock()
        report.id = 42
        report.access_token = 'abc-123-uuid'
        report.test_type.name = 'CBC'
        report.created_at.strftime.return_value = '10 March 2026'

        report.test_order.center.name = 'Popular Diagnostic'
        report.test_order.patient.get_full_name.return_value = 'Fatima Khan'
        return report

    @patch('apps.diagnostics.services.notifications.send_mail')
    def test_sends_email_successfully(self, mock_send_mail):
        report = self._make_mock_report()
        mock_send_mail.return_value = 1

        result = send_report_ready_email(report, 'patient@example.com')

        self.assertTrue(result)
        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args
        self.assertIn('Popular Diagnostic', call_kwargs.kwargs['subject'])
        self.assertIn('patient@example.com', call_kwargs.kwargs['recipient_list'])

    @patch('apps.diagnostics.services.notifications.send_mail')
    def test_email_body_contains_report_url(self, mock_send_mail):
        report = self._make_mock_report()
        mock_send_mail.return_value = 1

        send_report_ready_email(report, 'patient@example.com')

        call_kwargs = mock_send_mail.call_args
        body = call_kwargs.kwargs['message']
        self.assertIn('abc-123-uuid', body)
        self.assertIn('Fatima Khan', body)
        self.assertIn('CBC', body)

    def test_returns_false_for_empty_email(self):
        report = self._make_mock_report()
        result = send_report_ready_email(report, '')
        self.assertFalse(result)

    def test_returns_false_for_none_email(self):
        report = self._make_mock_report()
        result = send_report_ready_email(report, None)
        self.assertFalse(result)

    @patch('apps.diagnostics.services.notifications.send_mail')
    def test_returns_false_on_mail_exception(self, mock_send_mail):
        report = self._make_mock_report()
        mock_send_mail.side_effect = Exception('SMTP error')

        result = send_report_ready_email(report, 'patient@example.com')

        self.assertFalse(result)

    @override_settings(FRONTEND_URL='https://lab.example.com')
    @patch('apps.diagnostics.services.notifications.send_mail')
    def test_uses_frontend_url_setting(self, mock_send_mail):
        report = self._make_mock_report()
        mock_send_mail.return_value = 1

        send_report_ready_email(report, 'patient@example.com')

        body = mock_send_mail.call_args.kwargs['message']
        self.assertIn('https://lab.example.com/report/abc-123-uuid', body)
