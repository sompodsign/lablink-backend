from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.subscriptions.models import Invoice, Subscription, SubscriptionPlan
from apps.subscriptions.tasks import (
    check_trial_expirations,
    generate_monthly_invoices,
    mark_overdue_invoices,
    send_trial_expiry_warning,
)
from core.tenants.models import DiagnosticCenter, Permission, Staff

User = get_user_model()


class SubscriptionPlanModelTests(TestCase):
    """Tests for SubscriptionPlan model."""

    def test_create_plan(self):
        plan = SubscriptionPlan.objects.create(
            name="Test Plan",
            slug="test-plan",
            price=Decimal("999.00"),
            trial_days=14,
            max_staff=10,
            features=["Feature A", "Feature B"],
        )
        self.assertEqual(plan.name, "Test Plan")
        self.assertEqual(plan.slug, "test-plan")
        self.assertEqual(plan.price, Decimal("999.00"))
        self.assertEqual(plan.trial_days, 14)
        self.assertEqual(plan.max_staff, 10)
        self.assertTrue(plan.is_active)
        self.assertIn("Test Plan", str(plan))

    def test_default_ordering(self):
        SubscriptionPlan.objects.create(
            name="Plan B", slug="plan-b", price=200, display_order=2
        )
        SubscriptionPlan.objects.create(
            name="Plan A", slug="plan-a", price=100, display_order=1
        )
        plans = list(SubscriptionPlan.objects.values_list("slug", flat=True))
        self.assertEqual(plans, ["plan-a", "plan-b"])


class SubscriptionModelTests(TestCase):
    """Tests for Subscription model."""

    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Starter", slug="starter", price=Decimal("2499"), trial_days=14
        )
        self.center = DiagnosticCenter.objects.create(
            name="Test Center", domain="test-center"
        )

    def test_create_trial_subscription(self):
        now = timezone.now()
        sub = Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            trial_start=now,
            trial_end=now + timedelta(days=14),
        )
        self.assertEqual(sub.status, "TRIAL")
        self.assertFalse(sub.is_trial_expired)
        self.assertIsNotNone(sub.days_remaining_trial)
        self.assertGreater(sub.days_remaining_trial, 0)

    def test_trial_expired_property(self):
        past = timezone.now() - timedelta(days=15)
        sub = Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            trial_start=past,
            trial_end=past + timedelta(days=14),
        )
        self.assertTrue(sub.is_trial_expired)
        self.assertEqual(sub.days_remaining_trial, 0)

    def test_active_subscription_no_trial_info(self):
        sub = Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
        )
        self.assertFalse(sub.is_trial_expired)
        self.assertIsNone(sub.days_remaining_trial)

    def test_str_representation(self):
        sub = Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
        )
        self.assertIn("Test Center", str(sub))
        self.assertIn("Starter", str(sub))
        self.assertIn("TRIAL", str(sub))


class InvoiceModelTests(TestCase):
    """Tests for Invoice model."""

    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Pro", slug="pro", price=Decimal("4999")
        )
        self.center = DiagnosticCenter.objects.create(
            name="Invoice Center", domain="inv-center"
        )
        self.sub = Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
        )

    def test_create_invoice(self):
        invoice = Invoice.objects.create(
            subscription=self.sub,
            amount=Decimal("4999.00"),
            due_date=timezone.now().date(),
            status=Invoice.Status.PENDING,
        )
        self.assertEqual(invoice.status, "PENDING")
        self.assertEqual(invoice.amount, Decimal("4999.00"))
        self.assertIsNone(invoice.paid_at)
        self.assertIn("Invoice #", str(invoice))


class CenterRegistrationAPITests(TestCase):
    """Tests for public center registration endpoint."""

    def setUp(self):
        self.client = APIClient()
        # Seed required plans (get_or_create to avoid conflicts with data migrations)
        SubscriptionPlan.objects.get_or_create(
            slug="trial",
            defaults={"name": "Free Trial", "price": 0, "trial_days": 14},
        )
        SubscriptionPlan.objects.get_or_create(
            slug="starter",
            defaults={
                "name": "Starter",
                "price": 2499,
                "trial_days": 14,
                "max_staff": 15,
            },
        )
        # Create at least one permission so role creation works
        Permission.objects.get_or_create(
            codename="view_patients",
            defaults={"name": "View Patients", "category": "Patients"},
        )

    def test_register_center_free_trial(self):
        data = {
            "center_name": "My New Center",
            "domain": "my-new-center",
            "admin_first_name": "John",
            "admin_last_name": "Doe",
            "admin_email": "john@example.com",
            "admin_password": "securepass123",
            "plan_slug": "trial",
        }
        response = self.client.post("/api/public/register-center/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["center"]["domain"], "my-new-center")
        self.assertEqual(response.data["subscription"]["status"], "TRIAL")
        self.assertIsNotNone(response.data["subscription"]["trial_end"])

        # Verify center created
        center = DiagnosticCenter.objects.get(domain="my-new-center")
        self.assertEqual(center.name, "My New Center")
        self.assertTrue(center.is_active)

        # Verify admin user created
        admin = User.objects.get(email="john@example.com")
        self.assertEqual(admin.center, center)

        # Verify subscription created
        sub = Subscription.objects.get(center=center)
        self.assertEqual(sub.status, "TRIAL")
        self.assertIsNotNone(sub.trial_end)

        # Verify staff record
        self.assertTrue(Staff.objects.filter(user=admin, center=center).exists())

    def test_register_center_paid_plan(self):
        data = {
            "center_name": "Paid Center",
            "domain": "paid-center",
            "admin_first_name": "Jane",
            "admin_last_name": "Smith",
            "admin_email": "jane@example.com",
            "admin_password": "securepass123",
            "plan_slug": "starter",
        }
        response = self.client.post("/api/public/register-center/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["subscription"]["status"], "ACTIVE")

        # Verify invoice created
        center = DiagnosticCenter.objects.get(domain="paid-center")
        sub = Subscription.objects.get(center=center)
        self.assertEqual(sub.status, "ACTIVE")
        invoice = Invoice.objects.get(subscription=sub)
        self.assertEqual(invoice.amount, Decimal("2499"))
        self.assertEqual(invoice.status, "PENDING")

    def test_register_duplicate_domain_rejected(self):
        DiagnosticCenter.objects.create(name="Existing", domain="existing")
        data = {
            "center_name": "Duplicate",
            "domain": "existing",
            "admin_first_name": "Test",
            "admin_last_name": "User",
            "admin_email": "test@example.com",
            "admin_password": "securepass123",
            "plan_slug": "trial",
        }
        response = self.client.post("/api/public/register-center/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("domain", response.data)

    def test_register_duplicate_email_rejected(self):
        User.objects.create_user(
            username="existing_user",
            email="taken@example.com",
            password="test123",
        )
        data = {
            "center_name": "Email Test",
            "domain": "email-test",
            "admin_first_name": "Test",
            "admin_last_name": "User",
            "admin_email": "taken@example.com",
            "admin_password": "securepass123",
            "plan_slug": "trial",
        }
        response = self.client.post("/api/public/register-center/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("admin_email", response.data)

    def test_register_reserved_domain_rejected(self):
        data = {
            "center_name": "Admin Center",
            "domain": "admin",
            "admin_first_name": "Test",
            "admin_last_name": "User",
            "admin_email": "admin@example.com",
            "admin_password": "securepass123",
            "plan_slug": "trial",
        }
        response = self.client.post("/api/public/register-center/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("domain", response.data)

    def test_register_invalid_plan_rejected(self):
        data = {
            "center_name": "Bad Plan",
            "domain": "bad-plan",
            "admin_first_name": "Test",
            "admin_last_name": "User",
            "admin_email": "badplan@example.com",
            "admin_password": "securepass123",
            "plan_slug": "nonexistent",
        }
        response = self.client.post("/api/public/register-center/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_required_fields(self):
        response = self.client.post("/api/public/register-center/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("center_name", response.data)
        self.assertIn("admin_first_name", response.data)

    def test_register_short_password_rejected(self):
        data = {
            "center_name": "Short PW",
            "domain": "short-pw",
            "admin_first_name": "Test",
            "admin_last_name": "User",
            "admin_email": "shortpw@example.com",
            "admin_password": "abc12",
            "plan_slug": "trial",
        }
        response = self.client.post("/api/public/register-center/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("admin_password", response.data)

    def test_register_numeric_password_rejected(self):
        data = {
            "center_name": "Numeric PW",
            "domain": "numeric-pw",
            "admin_first_name": "Test",
            "admin_last_name": "User",
            "admin_email": "numericpw@example.com",
            "admin_password": "12345678",
            "plan_slug": "trial",
        }
        response = self.client.post("/api/public/register-center/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("admin_password", response.data)

    def test_register_common_password_rejected(self):
        data = {
            "center_name": "Common PW",
            "domain": "common-pw",
            "admin_first_name": "Test",
            "admin_last_name": "User",
            "admin_email": "commonpw@example.com",
            "admin_password": "password",
            "plan_slug": "trial",
        }
        response = self.client.post("/api/public/register-center/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("admin_password", response.data)

    def test_register_invalid_phone_rejected(self):
        data = {
            "center_name": "Phone Test",
            "domain": "phone-test",
            "admin_first_name": "Test",
            "admin_last_name": "User",
            "admin_email": "phonetest@example.com",
            "admin_password": "SecurePass123!",
            "admin_phone": "123",
            "plan_slug": "trial",
        }
        response = self.client.post("/api/public/register-center/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("admin_phone", response.data)


class PublicPlansAPITests(TestCase):
    """Tests for public plans list endpoint."""

    def setUp(self):
        self.client = APIClient()
        SubscriptionPlan.objects.create(
            name="Trial", slug="trial", price=0, is_active=True, display_order=0
        )
        SubscriptionPlan.objects.create(
            name="Hidden", slug="hidden", price=999, is_active=False, display_order=5
        )

    def test_list_active_plans_only(self):
        response = self.client.get("/api/public/plans/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = [p["slug"] for p in response.data]
        self.assertIn("trial", slugs)
        self.assertNotIn("hidden", slugs)


class SuperadminBillingAPITests(TestCase):
    """Tests for superadmin subscription/invoice management."""

    def setUp(self):
        self.client = APIClient()
        self.superadmin = User.objects.create_superuser(
            username="superadmin",
            email="super@admin.com",
            password="admin123",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Starter", slug="starter", price=2499
        )
        self.center = DiagnosticCenter.objects.create(
            name="Billing Test Center", domain="billing-test"
        )
        self.sub = Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
        )
        self.invoice = Invoice.objects.create(
            subscription=self.sub,
            amount=Decimal("2499"),
            due_date=timezone.now().date(),
            status=Invoice.Status.PENDING,
        )

    def test_list_subscriptions_requires_auth(self):
        response = self.client.get("/api/subscriptions/subscriptions/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_subscriptions_as_superadmin(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get("/api/subscriptions/subscriptions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)
        self.assertEqual(response.data[0]["center_name"], "Billing Test Center")

    def test_list_invoices_as_superadmin(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get("/api/subscriptions/invoices/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_mark_invoice_paid(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.post(
            f"/api/subscriptions/invoices/{self.invoice.id}/mark-paid/",
            {"payment_method": "CASH"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PAID")
        self.assertIsNotNone(self.invoice.paid_at)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "ACTIVE")

    def test_mark_already_paid_invoice(self):
        self.client.force_authenticate(self.superadmin)
        self.invoice.status = Invoice.Status.PAID
        self.invoice.save()
        response = self.client.post(
            f"/api/subscriptions/invoices/{self.invoice.id}/mark-paid/",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TrialExpiryTaskTests(TestCase):
    """Tests for Celery trial expiry tasks."""

    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Trial Plan", slug="trial", price=0, trial_days=14
        )

    def _make_sub(self, trial_end_offset_days):
        center = DiagnosticCenter.objects.create(
            name=f"Center {trial_end_offset_days}",
            domain=f"center-{abs(trial_end_offset_days)}",
        )
        now = timezone.now()
        return Subscription.objects.create(
            center=center,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            trial_start=now - timedelta(days=14),
            trial_end=now + timedelta(days=trial_end_offset_days),
        )

    def test_expire_past_trials(self):
        expired_sub = self._make_sub(-1)  # ended yesterday
        active_sub = self._make_sub(7)  # ends in 7 days

        count = check_trial_expirations()
        self.assertEqual(count, 1)

        expired_sub.refresh_from_db()
        self.assertEqual(expired_sub.status, "EXPIRED")

        active_sub.refresh_from_db()
        self.assertEqual(active_sub.status, "TRIAL")

    def test_no_expired_trials(self):
        self._make_sub(10)
        count = check_trial_expirations()
        self.assertEqual(count, 0)

    def test_warning_for_expiring_soon(self):
        self._make_sub(2)  # expires in 2 days — should warn
        self._make_sub(10)  # expires in 10 days — no warn

        count = send_trial_expiry_warning()
        self.assertEqual(count, 1)


class GenerateMonthlyInvoicesTaskTests(TestCase):
    """Tests for generate_monthly_invoices Celery task."""

    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Starter", slug="starter", price=Decimal("2499"), trial_days=14
        )

    def test_generates_invoice_when_billing_date_due(self):
        center = DiagnosticCenter.objects.create(name="Due Center", domain="due-center")
        today = timezone.now().date()
        sub = Subscription.objects.create(
            center=center,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            billing_date=today,
        )

        count = generate_monthly_invoices()
        self.assertEqual(count, 1)

        # Invoice created
        invoice = Invoice.objects.get(subscription=sub)
        self.assertEqual(invoice.amount, Decimal("2499"))
        self.assertEqual(invoice.status, "PENDING")
        self.assertEqual(invoice.due_date, today)

        # Billing date advanced by 30 days
        sub.refresh_from_db()
        from datetime import timedelta

        self.assertEqual(sub.billing_date, today + timedelta(days=30))

    def test_no_invoice_if_billing_date_in_future(self):
        center = DiagnosticCenter.objects.create(
            name="Future Center", domain="future-center"
        )
        future = timezone.now().date() + timedelta(days=10)
        Subscription.objects.create(
            center=center,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            billing_date=future,
        )

        count = generate_monthly_invoices()
        self.assertEqual(count, 0)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_no_duplicate_invoice_for_same_billing_cycle(self):
        center = DiagnosticCenter.objects.create(name="Dup Center", domain="dup-center")
        today = timezone.now().date()
        sub = Subscription.objects.create(
            center=center,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            billing_date=today,
        )
        # Pre-create invoice for today
        Invoice.objects.create(
            subscription=sub,
            amount=Decimal("2499"),
            due_date=today,
            status=Invoice.Status.PENDING,
        )

        count = generate_monthly_invoices()
        self.assertEqual(count, 0)
        self.assertEqual(Invoice.objects.filter(subscription=sub).count(), 1)

    def test_skips_trial_subscriptions(self):
        center = DiagnosticCenter.objects.create(
            name="Trial Center", domain="trial-skip"
        )
        Subscription.objects.create(
            center=center,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            billing_date=timezone.now().date(),
        )

        count = generate_monthly_invoices()
        self.assertEqual(count, 0)


class MarkOverdueInvoicesTaskTests(TestCase):
    """Tests for mark_overdue_invoices Celery task."""

    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Pro", slug="pro", price=Decimal("4999")
        )
        self.center = DiagnosticCenter.objects.create(
            name="Overdue Center", domain="overdue-center"
        )
        self.sub = Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
        )

    def test_marks_past_due_invoices_as_overdue(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        invoice = Invoice.objects.create(
            subscription=self.sub,
            amount=Decimal("4999"),
            due_date=yesterday,
            status=Invoice.Status.PENDING,
        )

        count = mark_overdue_invoices()
        self.assertEqual(count, 1)

        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "OVERDUE")

    def test_does_not_mark_future_invoices(self):
        tomorrow = timezone.now().date() + timedelta(days=1)
        Invoice.objects.create(
            subscription=self.sub,
            amount=Decimal("4999"),
            due_date=tomorrow,
            status=Invoice.Status.PENDING,
        )

        count = mark_overdue_invoices()
        self.assertEqual(count, 0)

    def test_does_not_affect_paid_invoices(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        Invoice.objects.create(
            subscription=self.sub,
            amount=Decimal("4999"),
            due_date=yesterday,
            status=Invoice.Status.PAID,
        )

        count = mark_overdue_invoices()
        self.assertEqual(count, 0)


class MarkInvoiceUnpaidAPITests(TestCase):
    """Tests for superadmin mark-unpaid endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.superadmin = User.objects.create_superuser(
            username="su_unpaid", email="su_unpaid@test.com", password="admin123"
        )
        plan = SubscriptionPlan.objects.create(
            name="Pro", slug="pro-unpaid", price=4999
        )
        center = DiagnosticCenter.objects.create(
            name="Unpaid Test", domain="unpaid-test"
        )
        self.sub = Subscription.objects.create(
            center=center, plan=plan, status=Subscription.Status.ACTIVE
        )
        self.invoice = Invoice.objects.create(
            subscription=self.sub,
            amount=Decimal("4999"),
            due_date=timezone.now().date(),
            status=Invoice.Status.PAID,
            paid_at=timezone.now(),
        )

    def test_mark_unpaid_success(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.post(
            f"/api/subscriptions/invoices/{self.invoice.id}/mark-unpaid/",
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PENDING")
        self.assertIsNone(self.invoice.paid_at)

    def test_mark_unpaid_already_pending(self):
        self.invoice.status = Invoice.Status.PENDING
        self.invoice.save()
        self.client.force_authenticate(self.superadmin)
        response = self.client.post(
            f"/api/subscriptions/invoices/{self.invoice.id}/mark-unpaid/",
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_mark_unpaid_requires_auth(self):
        response = self.client.post(
            f"/api/subscriptions/invoices/{self.invoice.id}/mark-unpaid/",
            format="json",
        )
        self.assertEqual(response.status_code, 401)


class SoftBlockMiddlewareTests(TestCase):
    """Tests for subscription soft-block in TenantMiddleware."""

    def setUp(self):
        self.client = APIClient()
        self.plan = SubscriptionPlan.objects.create(
            name="Pro", slug="pro-sb", price=4999
        )
        self.center = DiagnosticCenter.objects.create(
            name="SoftBlock Center", domain="softblock"
        )
        Permission.objects.get_or_create(
            codename="view_patients",
            defaults={"name": "View Patients", "category": "Patients"},
        )
        self.admin = User.objects.create_user(
            username="sb_admin", email="sb@test.com", password="test123"
        )
        self.admin.center = self.center
        self.admin.save()

        # Get JWT token for middleware to see
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken.for_user(self.admin)
        self.auth_header = f"Bearer {token.access_token}"

    def tearDown(self):
        from django.core.cache import cache

        cache.clear()

    def test_expired_subscription_blocks_post(self):
        Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.EXPIRED,
        )
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.post(
            "/api/diagnostics/test-orders/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 402)

    def test_expired_subscription_allows_get(self):
        Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.EXPIRED,
        )
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.get("/api/diagnostics/test-orders/")
        self.assertNotEqual(response.status_code, 402)

    def test_expired_subscription_allows_subscription_urls(self):
        Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.EXPIRED,
        )
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.get("/api/subscriptions/status/")
        self.assertNotEqual(response.status_code, 402)

    def test_active_subscription_allows_post(self):
        Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
        )
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.post(
            "/api/diagnostics/test-orders/",
            {},
            format="json",
        )
        self.assertNotEqual(response.status_code, 402)

    def test_superadmin_bypasses_soft_block(self):
        Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.EXPIRED,
        )
        superadmin = User.objects.create_superuser(
            username="su_bypass", email="su_bypass@test.com", password="admin123"
        )
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken.for_user(superadmin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        response = self.client.post(
            "/api/diagnostics/test-orders/",
            {},
            format="json",
        )
        self.assertNotEqual(response.status_code, 402)

    def test_no_subscription_blocks_post(self):
        """Centers with no subscription record should be soft-blocked."""
        # No subscription created for self.center
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.post(
            "/api/diagnostics/test-orders/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 402)


class SubscriptionStatusAPITests(TestCase):
    """Tests for subscription status endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.plan = SubscriptionPlan.objects.create(
            name="Status Plan", slug="status-plan", price=999
        )
        self.center = DiagnosticCenter.objects.create(
            name="Status Center", domain="status-center"
        )
        self.user = User.objects.create_user(
            username="status_user", email="status@test.com", password="test123"
        )
        self.user.center = self.center
        self.user.save()

        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken.for_user(self.user)
        self.auth_header = f"Bearer {token.access_token}"

    def tearDown(self):
        from django.core.cache import cache

        cache.clear()

    def test_returns_active_status(self):
        Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
        )
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.get("/api/subscriptions/status/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ACTIVE")
        self.assertFalse(response.data["is_blocked"])

    def test_returns_expired_status(self):
        Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.EXPIRED,
        )
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.get("/api/subscriptions/status/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "EXPIRED")
        self.assertTrue(response.data["is_blocked"])

    def test_requires_auth(self):
        response = self.client.get("/api/subscriptions/status/")
        self.assertEqual(response.status_code, 401)

    def test_none_status_is_blocked(self):
        """Centers without any subscription should be blocked."""
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.get("/api/subscriptions/status/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "NONE")
        self.assertTrue(response.data["is_blocked"])

    def test_status_includes_staff_limit_info(self):
        """Status API should return max_staff, current_staff_count, staff_limit_reached."""
        plan = SubscriptionPlan.objects.create(
            name="Limit Plan",
            slug="limit-plan",
            price=999,
            max_staff=10,
        )
        Subscription.objects.create(
            center=self.center,
            plan=plan,
            status=Subscription.Status.ACTIVE,
        )
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.get("/api/subscriptions/status/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["max_staff"], 10)
        self.assertIn("current_staff_count", response.data)
        self.assertFalse(response.data["staff_limit_reached"])

    def test_status_includes_report_limit_info(self):
        """Status API should return max_reports, current_report_count, report_limit_reached."""
        plan = SubscriptionPlan.objects.create(
            name="Report Plan",
            slug="report-plan",
            price=999,
            max_staff=10,
            max_reports=500,
        )
        Subscription.objects.create(
            center=self.center,
            plan=plan,
            status=Subscription.Status.ACTIVE,
        )
        self.client.credentials(HTTP_AUTHORIZATION=self.auth_header)
        response = self.client.get("/api/subscriptions/status/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["max_reports"], 500)
        self.assertIn("current_report_count", response.data)
        self.assertFalse(response.data["report_limit_reached"])


class SuperadminExtendTrialTests(TestCase):
    """Tests for superadmin extend-trial endpoint."""

    def setUp(self):
        from datetime import timedelta

        from django.utils import timezone
        from rest_framework_simplejwt.tokens import RefreshToken

        self.client = APIClient()
        self.plan = SubscriptionPlan.objects.create(
            name="Trial Plan", slug="extend-trial-plan", price=0, trial_days=14
        )
        self.center = DiagnosticCenter.objects.create(
            name="Extend Center", domain="extend-center"
        )
        now = timezone.now()
        self.sub = Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            trial_start=now,
            trial_end=now + timedelta(days=14),
        )

        self.superadmin = User.objects.create_superuser(
            username="sa_extend", email="sa_extend@test.com", password="test123"
        )
        token = RefreshToken.for_user(self.superadmin)
        self.auth = f"Bearer {token.access_token}"

        self.regular = User.objects.create_user(
            username="reg_extend", email="reg_extend@test.com", password="test123"
        )
        reg_token = RefreshToken.for_user(self.regular)
        self.reg_auth = f"Bearer {reg_token.access_token}"

    def tearDown(self):
        from django.core.cache import cache

        cache.clear()

    def test_extend_active_trial(self):
        old_end = self.sub.trial_end
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            f"/api/subscriptions/subscriptions/{self.sub.id}/extend-trial/",
            {"days": 7},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "TRIAL")
        self.assertGreater(self.sub.trial_end, old_end)

    def test_extend_expired_trial_resets_from_now(self):
        from datetime import timedelta

        from django.utils import timezone

        self.sub.status = Subscription.Status.EXPIRED
        self.sub.trial_end = timezone.now() - timedelta(days=5)
        self.sub.save()

        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            f"/api/subscriptions/subscriptions/{self.sub.id}/extend-trial/",
            {"days": 14},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "TRIAL")
        self.assertGreater(self.sub.trial_end, timezone.now())

    def test_extend_trial_invalid_days(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            f"/api/subscriptions/subscriptions/{self.sub.id}/extend-trial/",
            {"days": -1},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_extend_trial_not_found(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            "/api/subscriptions/subscriptions/99999/extend-trial/",
            {"days": 7},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_non_superadmin_denied(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.reg_auth)
        response = self.client.post(
            f"/api/subscriptions/subscriptions/{self.sub.id}/extend-trial/",
            {"days": 7},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class SuperadminChangePlanTests(TestCase):
    """Tests for superadmin change-plan endpoint."""

    def setUp(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        self.client = APIClient()
        self.trial_plan = SubscriptionPlan.objects.create(
            name="Trial", slug="change-trial", price=0, trial_days=14
        )
        self.starter_plan = SubscriptionPlan.objects.create(
            name="Starter", slug="change-starter", price=2499
        )
        self.center = DiagnosticCenter.objects.create(
            name="Plan Center", domain="plan-center"
        )
        self.sub = Subscription.objects.create(
            center=self.center,
            plan=self.trial_plan,
            status=Subscription.Status.TRIAL,
        )

        self.superadmin = User.objects.create_superuser(
            username="sa_plan", email="sa_plan@test.com", password="test123"
        )
        token = RefreshToken.for_user(self.superadmin)
        self.auth = f"Bearer {token.access_token}"

    def tearDown(self):
        from django.core.cache import cache

        cache.clear()

    def test_change_plan_activates_subscription(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            f"/api/subscriptions/subscriptions/{self.sub.id}/change-plan/",
            {"plan_id": self.starter_plan.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.plan, self.starter_plan)
        self.assertEqual(self.sub.status, "ACTIVE")
        self.assertIsNotNone(self.sub.billing_date)

    def test_change_plan_missing_plan_id(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            f"/api/subscriptions/subscriptions/{self.sub.id}/change-plan/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_change_plan_invalid_plan_id(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            f"/api/subscriptions/subscriptions/{self.sub.id}/change-plan/",
            {"plan_id": 99999},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_change_plan_not_found_subscription(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            "/api/subscriptions/subscriptions/99999/change-plan/",
            {"plan_id": self.starter_plan.id},
            format="json",
        )
        self.assertEqual(response.status_code, 404)


class SuperadminCreateInvoiceTests(TestCase):
    """Tests for superadmin create-invoice endpoint."""

    def setUp(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        self.client = APIClient()
        self.plan = SubscriptionPlan.objects.create(
            name="Invoice Plan", slug="invoice-plan", price=2499
        )
        self.center = DiagnosticCenter.objects.create(
            name="Invoice Center", domain="invoice-center"
        )
        self.sub = Subscription.objects.create(
            center=self.center,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
        )
        self.superadmin = User.objects.create_superuser(
            username="sa_invoice", email="sa_invoice@test.com", password="test123"
        )
        token = RefreshToken.for_user(self.superadmin)
        self.auth = f"Bearer {token.access_token}"

    def test_create_invoice_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            f"/api/subscriptions/subscriptions/{self.sub.id}/create-invoice/",
            {"amount": "2499.00", "due_date": "2026-04-15", "notes": "Custom"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("invoice", response.data)
        self.assertEqual(Invoice.objects.filter(subscription=self.sub).count(), 1)

    def test_create_invoice_missing_amount(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            f"/api/subscriptions/subscriptions/{self.sub.id}/create-invoice/",
            {"due_date": "2026-04-15"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_invoice_missing_due_date(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            f"/api/subscriptions/subscriptions/{self.sub.id}/create-invoice/",
            {"amount": "1000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_invoice_invalid_amount(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            f"/api/subscriptions/subscriptions/{self.sub.id}/create-invoice/",
            {"amount": "-500", "due_date": "2026-04-15"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_invoice_not_found(self):
        self.client.credentials(HTTP_AUTHORIZATION=self.auth)
        response = self.client.post(
            "/api/subscriptions/subscriptions/99999/create-invoice/",
            {"amount": "1000", "due_date": "2026-04-15"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
