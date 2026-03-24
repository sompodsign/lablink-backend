import logging
from unittest.mock import patch

from django.test import SimpleTestCase

logger = logging.getLogger(__name__)


class CelerySmsTaskTests(SimpleTestCase):
    """Test the send_sms_task Celery task."""

    @patch("apps.notifications.sms.send_sms")
    def test_send_sms_task_returns_confirmation(self, mock_send_sms):
        from apps.notifications.tasks import send_sms_task

        mock_send_sms.return_value = True
        result = send_sms_task("01700000001", "Test message")
        self.assertTrue(result)
        mock_send_sms.assert_called_once_with(
            phone_number="01700000001", message="Test message"
        )

    @patch("apps.notifications.sms.send_sms")
    def test_send_sms_task_passes_phone_number(self, mock_send_sms):
        from apps.notifications.tasks import send_sms_task

        send_sms_task("01712345678", "Your report is ready")
        mock_send_sms.assert_called_once()
        call_kwargs = mock_send_sms.call_args.kwargs
        self.assertEqual(call_kwargs["phone_number"], "01712345678")
