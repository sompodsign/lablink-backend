import logging
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from apps.notifications.emails import EmailType, send_email, send_email_async
from apps.notifications.templates import TEMPLATES

logger = logging.getLogger(__name__)


class TemplateRegistryTests(SimpleTestCase):
    """Verify all EmailType keys have corresponding templates."""

    def test_all_email_types_have_templates(self):
        for email_type in EmailType:
            self.assertIn(
                str(email_type),
                TEMPLATES,
                f'Missing template for EmailType.{email_type.name}',
            )

    def test_templates_are_tuples_of_two_strings(self):
        for key, template in TEMPLATES.items():
            self.assertIsInstance(template, tuple, f'{key}: not a tuple')
            self.assertEqual(len(template), 2, f'{key}: expected 2 elements')
            self.assertIsInstance(template[0], str, f'{key}: subject not str')
            self.assertIsInstance(template[1], str, f'{key}: body not str')


class SendEmailTests(SimpleTestCase):
    """Test the send_email() dispatcher."""

    @override_settings(DEFAULT_FROM_EMAIL='test@lablink.bd')
    @patch('apps.notifications.emails.send_mail')
    def test_send_email_success(self, mock_send_mail):
        result = send_email(
            EmailType.WELCOME_PATIENT,
            recipient='patient@example.com',
            context={
                'patient_name': 'John Doe',
                'center_name': 'Alpha Lab',
                'login_url': 'http://alpha-lab.localhost/login',
            },
        )
        self.assertTrue(result)
        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args
        self.assertIn('Alpha Lab', call_kwargs.kwargs['subject'])
        self.assertIn('John Doe', call_kwargs.kwargs['message'])

    @patch('apps.notifications.emails.send_mail')
    def test_send_email_unknown_type_returns_false(self, mock_send_mail):
        result = send_email(
            'nonexistent_type',
            recipient='test@example.com',
            context={},
        )
        self.assertFalse(result)
        mock_send_mail.assert_not_called()

    @patch('apps.notifications.emails.send_mail')
    def test_send_email_empty_recipient_returns_false(self, mock_send_mail):
        result = send_email(
            EmailType.WELCOME_PATIENT,
            recipient='',
            context={
                'patient_name': 'John',
                'center_name': 'Lab',
                'login_url': 'http://test',
            },
        )
        self.assertFalse(result)
        mock_send_mail.assert_not_called()

    @patch('apps.notifications.emails.send_mail')
    def test_send_email_missing_context_key_returns_false(self, mock_send_mail):
        result = send_email(
            EmailType.WELCOME_PATIENT,
            recipient='test@example.com',
            context={'patient_name': 'John'},  # missing center_name, login_url
        )
        self.assertFalse(result)
        mock_send_mail.assert_not_called()

    @override_settings(DEFAULT_FROM_EMAIL='test@lablink.bd')
    @patch('apps.notifications.emails.send_mail', side_effect=Exception('SMTP error'))
    def test_send_email_smtp_failure_returns_false(self, mock_send_mail):
        result = send_email(
            EmailType.PASSWORD_RESET,
            recipient='test@example.com',
            context={
                'user_name': 'John',
                'reset_url': 'http://test/reset',
            },
        )
        self.assertFalse(result)

    @override_settings(DEFAULT_FROM_EMAIL='test@lablink.bd')
    @patch('apps.notifications.emails.send_mail')
    def test_send_email_custom_from_email(self, mock_send_mail):
        send_email(
            EmailType.PASSWORD_RESET,
            recipient='test@example.com',
            context={
                'user_name': 'John',
                'reset_url': 'http://test/reset',
            },
            from_email='custom@lablink.bd',
        )
        call_kwargs = mock_send_mail.call_args
        self.assertEqual(call_kwargs.kwargs['from_email'], 'custom@lablink.bd')


class SendEmailAsyncTests(SimpleTestCase):
    """Test async dispatch to Celery."""

    @patch('apps.notifications.tasks.send_email_task.delay')
    def test_send_email_async_dispatches_to_celery(self, mock_delay):
        send_email_async(
            EmailType.APPOINTMENT_BOOKED,
            recipient='test@example.com',
            context={'patient_name': 'A', 'center_name': 'B',
                     'doctor_name': 'C', 'date': '2026-01-01', 'time': '10:00'},
        )
        mock_delay.assert_called_once()


class CeleryTaskTests(SimpleTestCase):
    """Test the send_email_task Celery task."""

    @override_settings(DEFAULT_FROM_EMAIL='test@lablink.bd')
    @patch('apps.notifications.emails.send_mail')
    def test_send_email_task_calls_send_email(self, mock_send_mail):
        from apps.notifications.tasks import send_email_task

        result = send_email_task(
            email_type='password_reset',
            recipient='test@example.com',
            context={
                'user_name': 'John',
                'reset_url': 'http://test/reset',
            },
        )
        self.assertTrue(result)
        mock_send_mail.assert_called_once()


class TemplateRenderingTests(SimpleTestCase):
    """Test each template renders without errors with correct context."""

    TEMPLATE_CONTEXTS = {
        'welcome_patient': {
            'patient_name': 'John', 'center_name': 'Lab', 'login_url': 'http://test',
        },
        'password_reset': {
            'user_name': 'John', 'reset_url': 'http://test/reset',
        },
        'password_reset_success': {
            'user_name': 'John',
        },
        'account_approved': {
            'patient_name': 'John', 'center_name': 'Lab', 'login_url': 'http://test',
        },
        'account_declined': {
            'patient_name': 'John', 'center_name': 'Lab',
        },
        'appointment_booked': {
            'patient_name': 'John', 'center_name': 'Lab',
            'doctor_name': 'Dr. Smith', 'date': '2026-01-01', 'time': '10:00',
        },
        'appointment_confirmed': {
            'patient_name': 'John', 'center_name': 'Lab',
            'doctor_name': 'Dr. Smith', 'date': '2026-01-01', 'time': '10:00',
        },
        'appointment_cancelled': {
            'patient_name': 'John', 'center_name': 'Lab',
            'date': '2026-01-01', 'time': '10:00',
        },
        'report_ready': {
            'patient_name': 'John', 'test_name': 'CBC',
            'report_date': '01 January 2026', 'center_name': 'Lab',
            'report_url': 'http://test/report/abc',
        },
        'staff_credentials': {
            'first_name': 'John', 'role_name': 'Admin',
            'center_name': 'Lab', 'username': 'john_doe', 'password': 'abc123',
        },
        'doctor_credentials': {
            'first_name': 'John', 'center_name': 'Lab',
            'username': 'dr_john', 'password': 'abc123',
        },
        'trial_expiry_warning': {
            'center_name': 'Lab', 'days_left': 3,
        },
        'trial_expired': {
            'center_name': 'Lab',
        },
        'invoice_generated': {
            'center_name': 'Lab', 'amount': '5000.00', 'due_date': '2026-02-01',
        },
        'invoice_overdue': {
            'center_name': 'Lab', 'amount': '5000.00', 'due_date': '2026-02-01',
        },
        'payment_received': {
            'center_name': 'Lab', 'amount': '5000.00', 'plan_name': 'Starter',
        },
        'center_created': {
            'center_name': 'Lab',
        },
        'center_deactivated': {
            'center_name': 'Lab',
        },
    }

    def test_all_templates_render_successfully(self):
        for key, template in TEMPLATES.items():
            context = self.TEMPLATE_CONTEXTS.get(key)
            self.assertIsNotNone(
                context,
                f'No test context defined for template: {key}',
            )
            subject_tpl, body_tpl = template
            try:
                subject = subject_tpl.format(**context)
                body = body_tpl.format(**context)
            except KeyError as e:
                self.fail(f'Template {key} missing context key: {e}')
            self.assertIsInstance(subject, str)
            self.assertIsInstance(body, str)
            self.assertTrue(len(subject) > 0, f'{key}: empty subject')
            self.assertTrue(len(body) > 0, f'{key}: empty body')
