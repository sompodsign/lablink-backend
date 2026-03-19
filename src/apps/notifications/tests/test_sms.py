import logging
from unittest.mock import patch

from django.test import SimpleTestCase

logger = logging.getLogger(__name__)


class SmsTaskTests(SimpleTestCase):
    """Test the send_sms_notification Celery task."""

    @patch("apps.notifications.tasks.logger")
    def test_send_sms_notification_returns_confirmation(self, mock_logger):
        from apps.notifications.tasks import send_sms_notification

        result = send_sms_notification("01700000001", "Test message")
        self.assertIn("sent", result.lower())

    @patch("apps.notifications.tasks.logger")
    def test_send_sms_notification_logs_phone_number(self, mock_logger):
        from apps.notifications.tasks import send_sms_notification

        send_sms_notification("01712345678", "Your report is ready")
        mock_logger.info.assert_called()
        log_args = str(mock_logger.info.call_args)
        self.assertIn("01712345678", log_args)
