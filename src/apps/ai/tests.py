from decimal import Decimal

from django.test import TestCase

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


class AIServiceTestBase(TestCase):
    """Common setup for AI service tests."""

    def setUp(self):
        self.center = DiagnosticCenter.objects.create(
            name="Test Lab",
            domain="testlab",
            address="123 Test St",
            contact_number="01700000000",
            can_use_ai=True,
        )
        self.plan, _ = SubscriptionPlan.objects.get_or_create(
            slug="professional",
            defaults={
                "name": "Professional",
                "price": Decimal("2000.00"),
                "monthly_ai_credits": 500,
            },
        )
        # Ensure AI credits are set even if plan already existed
        if self.plan.monthly_ai_credits != 500:
            self.plan.monthly_ai_credits = 500
            self.plan.save(update_fields=["monthly_ai_credits"])
        self.subscription = Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            available_ai_credits=500,
        )
        self.user = User.objects.create_user(
            username="tech_user",
            password="testpass123",
            center=self.center,
        )


class CheckAIAccessTests(AIServiceTestBase):
    """Tests for the check_ai_access pre-flight function."""

    def test_access_granted_returns_subscription(self):
        result = check_ai_access(self.center)
        self.assertEqual(result.id, self.subscription.id)

    def test_ai_disabled_raises_error(self):
        self.center.can_use_ai = False
        self.center.save(update_fields=["can_use_ai"])
        with self.assertRaises(AIFeatureDisabledError):
            check_ai_access(self.center)

    def test_no_active_subscription_raises_error(self):
        self.subscription.status = Subscription.Status.EXPIRED
        self.subscription.save(update_fields=["status"])
        with self.assertRaises(AIFeatureDisabledError):
            check_ai_access(self.center)

    def test_zero_credits_raises_error(self):
        self.subscription.available_ai_credits = 0
        self.subscription.save(update_fields=["available_ai_credits"])
        with self.assertRaises(InsufficientAICreditsError):
            check_ai_access(self.center)

    def test_trial_subscription_allows_access(self):
        self.subscription.status = Subscription.Status.TRIAL
        self.subscription.save(update_fields=["status"])
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
            metadata={"session_id": "abc123"},
        )
        self.assertEqual(log.input_tokens, 150)
        self.assertEqual(log.output_tokens, 200)
        self.assertEqual(log.metadata, {"session_id": "abc123"})

    def test_deduct_fails_with_zero_credits(self):
        self.subscription.available_ai_credits = 0
        self.subscription.save(update_fields=["available_ai_credits"])
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
        self.subscription.save(update_fields=["available_ai_credits"])
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
        self.assertIn("Report Extraction", str(log))
        self.assertIn("1 credit(s)", str(log))
