"""Tests for AI report extraction endpoint and existing credit system."""

from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.ai.models import AICreditUsageLog
from apps.ai.services import (
    AIFeatureDisabledError,
    InsufficientAICreditsError,
    check_ai_access,
    deduct_ai_credit,
)
from apps.subscriptions.models import Subscription, SubscriptionPlan
from core.tenants.models import DiagnosticCenter
from core.users.models import User
from helpers.test_factories import (
    jwt_auth_header,
    make_center,
    make_report_template,
    make_staff,
    make_test_type,
    make_user,
)


# ── Existing credit system tests (unchanged) ─────────────────────


class AIServiceTestBase(TestCase):
    """Common setup for AI service tests."""

    def setUp(self):
        self.center = DiagnosticCenter.objects.create(
            name='Test Lab',
            domain='testlab',
            address='123 Test St',
            contact_number='01700000000',
            can_use_ai=True,
        )
        self.plan, _ = SubscriptionPlan.objects.get_or_create(
            slug='professional',
            defaults={
                'name': 'Professional',
                'price': Decimal('2000.00'),
                'monthly_ai_credits': 500,
            },
        )
        # Ensure AI credits are set even if plan already existed
        if self.plan.monthly_ai_credits != 500:
            self.plan.monthly_ai_credits = 500
            self.plan.save(update_fields=['monthly_ai_credits'])
        self.subscription = Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            available_ai_credits=500,
        )
        self.user = User.objects.create_user(
            username='tech_user',
            password='testpass123',
            center=self.center,
        )


class CheckAIAccessTests(AIServiceTestBase):
    """Tests for the check_ai_access pre-flight function."""

    def test_access_granted_returns_subscription(self):
        result = check_ai_access(self.center)
        self.assertEqual(result.id, self.subscription.id)

    def test_ai_disabled_raises_error(self):
        self.center.can_use_ai = False
        self.center.save(update_fields=['can_use_ai'])
        with self.assertRaises(AIFeatureDisabledError):
            check_ai_access(self.center)

    def test_center_admin_toggle_disabled_raises_error(self):
        self.center.use_ai = False
        self.center.save(update_fields=['use_ai'])
        with self.assertRaises(AIFeatureDisabledError):
            check_ai_access(self.center)

    def test_no_active_subscription_raises_error(self):
        self.subscription.status = Subscription.Status.EXPIRED
        self.subscription.save(update_fields=['status'])
        with self.assertRaises(AIFeatureDisabledError):
            check_ai_access(self.center)

    def test_zero_credits_raises_error(self):
        self.subscription.available_ai_credits = 0
        self.subscription.save(update_fields=['available_ai_credits'])
        with self.assertRaises(InsufficientAICreditsError):
            check_ai_access(self.center)

    def test_trial_subscription_allows_access(self):
        self.subscription.status = Subscription.Status.TRIAL
        self.subscription.save(update_fields=['status'])
        result = check_ai_access(self.center)
        self.assertEqual(result.id, self.subscription.id)


class DeductAICreditTests(AIServiceTestBase):
    """Tests for the deduct_ai_credit atomic deduction function."""

    def test_deduct_single_credit(self):
        log = deduct_ai_credit(
            center=self.center,
            task_type=AICreditUsageLog.TaskType.REPORT_EXTRACTION,
            performed_by=self.user,
        )
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.available_ai_credits, 499)
        self.assertEqual(log.credits_used, 1)
        self.assertEqual(
            log.task_type,
            AICreditUsageLog.TaskType.REPORT_EXTRACTION,
        )

    def test_deduct_with_token_counts(self):
        log = deduct_ai_credit(
            center=self.center,
            task_type=AICreditUsageLog.TaskType.CHATBOT_SESSION,
            performed_by=self.user,
            input_tokens=150,
            output_tokens=200,
            metadata={'session_id': 'abc123'},
        )
        self.assertEqual(log.input_tokens, 150)
        self.assertEqual(log.output_tokens, 200)
        self.assertEqual(log.metadata, {'session_id': 'abc123'})

    def test_deduct_fails_with_zero_credits(self):
        self.subscription.available_ai_credits = 0
        self.subscription.save(update_fields=['available_ai_credits'])
        with self.assertRaises(InsufficientAICreditsError):
            deduct_ai_credit(
                center=self.center,
                task_type=AICreditUsageLog.TaskType.REPORT_EXTRACTION,
            )

    def test_deduct_multiple_credits(self):
        log = deduct_ai_credit(
            center=self.center,
            task_type=AICreditUsageLog.TaskType.REPORT_EXTRACTION,
            credits=5,
        )
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.available_ai_credits, 495)
        self.assertEqual(log.credits_used, 5)

    def test_deduct_creates_log_entry(self):
        self.assertEqual(AICreditUsageLog.objects.count(), 0)
        deduct_ai_credit(
            center=self.center,
            task_type=AICreditUsageLog.TaskType.REPORT_EXTRACTION,
            performed_by=self.user,
        )
        self.assertEqual(AICreditUsageLog.objects.count(), 1)
        log = AICreditUsageLog.objects.first()
        self.assertEqual(log.center, self.center)
        self.assertEqual(log.performed_by, self.user)

    def test_deduct_atomicity_no_partial_deduction(self):
        """If deduction fails, credits should not change."""
        self.subscription.available_ai_credits = 3
        self.subscription.save(update_fields=['available_ai_credits'])
        with self.assertRaises(InsufficientAICreditsError):
            deduct_ai_credit(
                center=self.center,
                task_type=AICreditUsageLog.TaskType.REPORT_EXTRACTION,
                credits=5,
            )
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.available_ai_credits, 3)


class AICreditUsageLogModelTests(AIServiceTestBase):
    """Tests for the AICreditUsageLog model."""

    def test_str_representation(self):
        log = AICreditUsageLog.objects.create(
            center=self.center,
            task_type=AICreditUsageLog.TaskType.REPORT_EXTRACTION,
            credits_used=1,
        )
        self.assertIn('Report Extraction', str(log))
        self.assertIn('1 credit(s)', str(log))


# ── Extract endpoint tests ───────────────────────────────────────


def _make_test_image(content_type='image/jpeg'):
    """Create a valid in-memory image file using PIL."""
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    img = Image.new('RGB', (10, 10), color='red')
    buf = BytesIO()
    fmt = 'JPEG' if 'jpeg' in content_type else 'PNG'
    img.save(buf, format=fmt)
    buf.seek(0)
    ext = 'jpg' if fmt == 'JPEG' else 'png'
    return SimpleUploadedFile(
        f'test_report.{ext}',
        buf.read(),
        content_type=content_type,
    )


MOCK_EXTRACTION_RESULT = {
    'Hemoglobin': {'value': '14.5', 'unit': 'g/dL', 'finding': 'Normal'},
    'Total WBC Count': {'value': '8500', 'unit': '/cumm', 'finding': 'Normal'},
}


class ReportExtractionEndpointTests(TestCase):
    """Tests for POST /api/ai/extract-report/."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.tt = make_test_type('CBC', '500.00')
        self.template = make_report_template(
            self.tt,
            self.center,
            fields=[
                {'name': 'Hemoglobin', 'unit': 'g/dL', 'ref_range': '13.5-17.5'},
                {'name': 'Total WBC Count', 'unit': '/cumm', 'ref_range': '4000-11000'},
            ],
        )

        # Staff user
        self.staff_user = make_user('staff1')
        make_staff(self.staff_user, self.center, role='Medical Technologist')
        self.auth = jwt_auth_header(self.staff_user)

        # Enable AI flags AFTER center creation (signals reset use_ai)
        self.center.can_use_ai = True
        self.center.use_ai = True
        self.center.save(update_fields=['can_use_ai', 'use_ai'])

        # Ensure subscription has AI credits
        sub = Subscription.objects.filter(center=self.center).first()
        sub.available_ai_credits = 100
        sub.save(update_fields=['available_ai_credits'])

    @patch('apps.ai.views.extract_report_data')
    def test_extract_success(self, mock_extract):
        from apps.ai.client import ExtractionResult

        mock_extract.return_value = ExtractionResult(
            result_data=MOCK_EXTRACTION_RESULT,
            input_tokens=500,
            output_tokens=200,
            model='claude-3-5-haiku-latest',
        )

        image = _make_test_image()
        resp = self.client.post(
            '/api/ai/extract-report/',
            {'image': image, 'test_type_id': self.tt.id},
            format='multipart',
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('result_data', resp.data)
        self.assertIn('Hemoglobin', resp.data['result_data'])
        self.assertIn('credits_remaining', resp.data)
        self.assertEqual(resp.data['credits_remaining'], 99)
        mock_extract.assert_called_once()

    @patch('apps.ai.views.extract_report_data')
    def test_extract_deducts_credit(self, mock_extract):
        from apps.ai.client import ExtractionResult

        mock_extract.return_value = ExtractionResult(
            result_data=MOCK_EXTRACTION_RESULT,
            input_tokens=500, output_tokens=200,
            model='claude-3-5-haiku-latest',
        )

        image = _make_test_image()
        self.client.post(
            '/api/ai/extract-report/',
            {'image': image, 'test_type_id': self.tt.id},
            format='multipart',
            **self.auth,
        )

        # Verify credit was deducted
        sub = Subscription.objects.get(center=self.center)
        self.assertEqual(sub.available_ai_credits, 99)

        # Verify log was created
        log = AICreditUsageLog.objects.filter(center=self.center).first()
        self.assertIsNotNone(log)
        self.assertEqual(
            log.task_type,
            AICreditUsageLog.TaskType.REPORT_EXTRACTION,
        )

    def test_extract_fails_when_ai_disabled(self):
        self.center.can_use_ai = False
        self.center.save(update_fields=['can_use_ai'])

        image = _make_test_image()
        resp = self.client.post(
            '/api/ai/extract-report/',
            {'image': image, 'test_type_id': self.tt.id},
            format='multipart',
            **self.auth,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn('not enabled', resp.data['detail'])

    def test_extract_fails_with_no_credits(self):
        sub = Subscription.objects.get(center=self.center)
        sub.available_ai_credits = 0
        sub.save(update_fields=['available_ai_credits'])

        image = _make_test_image()
        resp = self.client.post(
            '/api/ai/extract-report/',
            {'image': image, 'test_type_id': self.tt.id},
            format='multipart',
            **self.auth,
        )
        self.assertEqual(resp.status_code, 402)
        self.assertIn('credit', resp.data['detail'].lower())

    def test_extract_fails_without_template(self):
        self.template.delete()

        image = _make_test_image()
        resp = self.client.post(
            '/api/ai/extract-report/',
            {'image': image, 'test_type_id': self.tt.id},
            format='multipart',
            **self.auth,
        )
        self.assertEqual(resp.status_code, 404)
        self.assertIn('template', resp.data['detail'].lower())

    def test_extract_rejects_unauthenticated(self):
        image = _make_test_image()
        resp = self.client.post(
            '/api/ai/extract-report/',
            {'image': image, 'test_type_id': self.tt.id},
            format='multipart',
        )
        self.assertEqual(resp.status_code, 401)

    def test_extract_rejects_missing_image(self):
        resp = self.client.post(
            '/api/ai/extract-report/',
            {'test_type_id': self.tt.id},
            format='multipart',
            **self.auth,
        )
        self.assertEqual(resp.status_code, 400)

    def test_extract_rejects_missing_test_type(self):
        image = _make_test_image()
        resp = self.client.post(
            '/api/ai/extract-report/',
            {'image': image},
            format='multipart',
            **self.auth,
        )
        self.assertEqual(resp.status_code, 400)
