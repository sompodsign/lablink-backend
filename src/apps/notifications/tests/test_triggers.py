"""Integration tests verifying each email trigger point fires the right email.

Every test patches the centralized dispatcher and asserts the correct
EmailType, recipient, and context keys are passed.
"""

import logging
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.emails import EmailType
from apps.subscriptions.models import Invoice, Subscription, SubscriptionPlan
from core.tenants.models import DiagnosticCenter, Permission
from helpers.test_factories import (
    jwt_auth_header,
    make_appointment,
    make_center,
    make_doctor,
    make_staff,
    make_user,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ── Auth & Account Trigger Tests ─────────────────────────────────


class WelcomePatientEmailTests(APITestCase):
    """RegisterView sends WELCOME_PATIENT email on signup."""

    @patch("core.users.views.send_email")
    def test_welcome_email_sent_on_registration(self, mock_send_email):
        mock_send_email.return_value = True
        payload = {
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "email": "welcome@test.com",
            "first_name": "Welcome",
            "last_name": "User",
        }
        response = self.client.post("/api/auth/register/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_send_email.assert_called_once()

        call_args = mock_send_email.call_args
        self.assertEqual(call_args.args[0], EmailType.WELCOME_PATIENT)
        self.assertEqual(call_args.kwargs["recipient"], "welcome@test.com")
        self.assertIn("patient_name", call_args.kwargs["context"])
        self.assertIn("login_url", call_args.kwargs["context"])

    @patch("core.users.views.send_email")
    def test_no_welcome_email_without_email(self, mock_send_email):
        """Users without email should not trigger welcome email."""
        payload = {
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "email": "",
            "first_name": "NoEmail",
            "last_name": "User",
        }
        # Email is required — should fail validation
        _response = self.client.post("/api/auth/register/", payload)
        # If it fails with 400, no email should be sent
        mock_send_email.assert_not_called()


class PasswordResetEmailTests(APITestCase):
    """PasswordResetRequestView sends PASSWORD_RESET email."""

    def setUp(self):
        self.user = make_user(
            "reset_user",
            email="reset@test.com",
            first_name="Reset",
            last_name="User",
        )

    @patch("core.users.views.send_email")
    def test_password_reset_email_sent(self, mock_send_email):
        mock_send_email.return_value = True
        response = self.client.post(
            "/api/auth/password-reset/",
            {"email": "reset@test.com"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email.assert_called_once()

        call_args = mock_send_email.call_args
        self.assertEqual(call_args.args[0], EmailType.PASSWORD_RESET)
        self.assertEqual(call_args.kwargs["recipient"], "reset@test.com")
        self.assertIn("reset_url", call_args.kwargs["context"])
        self.assertIn("user_name", call_args.kwargs["context"])

    @patch("core.users.views.send_email")
    def test_no_email_for_unknown_user(self, mock_send_email):
        response = self.client.post(
            "/api/auth/password-reset/",
            {"email": "nobody@test.com"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email.assert_not_called()


class PasswordResetSuccessEmailTests(APITestCase):
    """PasswordResetConfirmView sends PASSWORD_RESET_SUCCESS email."""

    def setUp(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        self.user = make_user(
            "confirm_user",
            email="confirm@test.com",
            first_name="Confirm",
            last_name="User",
        )
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)

    @patch("core.users.views.send_email")
    def test_success_email_sent_on_password_change(self, mock_send_email):
        mock_send_email.return_value = True
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "NewSecurePass123!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email.assert_called_once()

        call_args = mock_send_email.call_args
        self.assertEqual(call_args.args[0], EmailType.PASSWORD_RESET_SUCCESS)
        self.assertEqual(call_args.kwargs["recipient"], "confirm@test.com")


# ── Staff & Doctor Credential Trigger Tests ──────────────────────


class StaffCredentialsEmailTests(APITestCase):
    """StaffCreateSerializer sends STAFF_CREDENTIALS email."""

    def setUp(self):
        self.center = make_center()
        self.staff_user = make_user("admin_staff", email="admin@center.com")
        make_staff(self.staff_user, self.center, "Admin")
        Permission.objects.get_or_create(
            codename="view_patients",
            defaults={"name": "View Patients", "category": "Patients"},
        )

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = f"{self.center.domain}.localhost"

    @patch("core.tenants.serializers.send_email")
    def test_staff_credentials_email_sent_on_create(self, mock_send_email):
        mock_send_email.return_value = True
        self._auth(self.staff_user)

        from helpers.test_factories import _get_or_create_role

        role = _get_or_create_role(self.center, "Medical Technologist")

        response = self.client.post(
            "/api/tenants/staff/",
            {
                "first_name": "New",
                "last_name": "Staff",
                "email": "newstaff@test.com",
                "role_id": role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_send_email.assert_called_once()

        call_args = mock_send_email.call_args
        self.assertEqual(call_args.args[0], EmailType.STAFF_CREDENTIALS)
        self.assertEqual(call_args.kwargs["recipient"], "newstaff@test.com")
        ctx = call_args.kwargs["context"]
        self.assertIn("username", ctx)
        self.assertIn("password", ctx)
        self.assertIn("center_name", ctx)
        self.assertIn("role_name", ctx)


class DoctorCredentialsEmailTests(APITestCase):
    """DoctorCreateSerializer sends DOCTOR_CREDENTIALS email."""

    def setUp(self):
        self.center = make_center()
        self.staff_user = make_user("doc_admin", email="docadmin@center.com")
        make_staff(self.staff_user, self.center, "Admin")

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = f"{self.center.domain}.localhost"

    @patch("core.tenants.serializers.send_email")
    def test_doctor_credentials_email_sent_on_create(self, mock_send_email):
        mock_send_email.return_value = True
        self._auth(self.staff_user)

        response = self.client.post(
            "/api/tenants/doctors/",
            {
                "first_name": "Dr",
                "last_name": "NewDoc",
                "email": "newdoc@test.com",
                "specialization": "General",
                "designation": "MD",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_send_email.assert_called_once()

        call_args = mock_send_email.call_args
        self.assertEqual(call_args.args[0], EmailType.DOCTOR_CREDENTIALS)
        self.assertEqual(call_args.kwargs["recipient"], "newdoc@test.com")
        ctx = call_args.kwargs["context"]
        self.assertIn("username", ctx)
        self.assertIn("password", ctx)
        self.assertIn("center_name", ctx)


# ── Appointment Trigger Tests ────────────────────────────────────


class AppointmentBookedEmailTests(APITestCase):
    """book() action sends APPOINTMENT_BOOKED email."""

    def setUp(self):
        self.center = make_center(allow_online_appointments=True)
        self.patient = make_user(
            "booking_patient",
            email="patient@test.com",
            first_name="Booking",
            last_name="Patient",
        )
        self.patient.center = self.center
        self.patient.save()
        self.doctor_user = make_user("booking_doc")
        self.doctor = make_doctor(self.doctor_user, self.center)

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = f"{self.center.domain}.localhost"

    @patch("apps.appointments.views.send_email_async")
    def test_booking_sends_email(self, mock_send_email_async):
        self._auth(self.patient)

        response = self.client.post(
            "/api/appointments/appointments/book/",
            {
                "doctor": self.doctor.id,
                "date": "2026-04-01",
                "time": "10:00",
                "symptoms": "Test symptoms",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_send_email_async.assert_called_once()

        call_args = mock_send_email_async.call_args
        self.assertEqual(call_args.args[0], EmailType.APPOINTMENT_BOOKED)
        self.assertEqual(call_args.kwargs["recipient"], "patient@test.com")
        ctx = call_args.kwargs["context"]
        self.assertIn("patient_name", ctx)
        self.assertIn("center_name", ctx)
        self.assertIn("doctor_name", ctx)
        self.assertIn("date", ctx)
        self.assertIn("time", ctx)


class AppointmentStatusChangeEmailTests(APITestCase):
    """partial_update() sends CONFIRMED/CANCELLED email on status change."""

    def setUp(self):
        self.center = make_center()
        self.staff_user = make_user("status_staff")
        make_staff(self.staff_user, self.center, "Admin")
        self.patient = make_user(
            "status_patient",
            email="status_pt@test.com",
            first_name="Status",
            last_name="Patient",
        )
        self.patient.center = self.center
        self.patient.save()
        self.doctor_user = make_user("status_doc")
        self.doctor = make_doctor(self.doctor_user, self.center)
        self.appointment = make_appointment(
            self.patient,
            self.center,
            self.doctor,
            status="PENDING",
        )

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = f"{self.center.domain}.localhost"

    @patch("apps.appointments.views.send_email_async")
    def test_confirming_appointment_sends_email(self, mock_send_email_async):
        self._auth(self.staff_user)

        response = self.client.patch(
            f"/api/appointments/appointments/{self.appointment.id}/",
            {"status": "CONFIRMED"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email_async.assert_called_once()

        call_args = mock_send_email_async.call_args
        self.assertEqual(call_args.args[0], EmailType.APPOINTMENT_CONFIRMED)
        self.assertEqual(call_args.args[1], "status_pt@test.com")

    @patch("apps.appointments.views.send_email_async")
    def test_cancelling_appointment_sends_email(self, mock_send_email_async):
        self._auth(self.staff_user)

        response = self.client.patch(
            f"/api/appointments/appointments/{self.appointment.id}/",
            {"status": "CANCELLED"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email_async.assert_called_once()

        call_args = mock_send_email_async.call_args
        self.assertEqual(call_args.args[0], EmailType.APPOINTMENT_CANCELLED)

    @patch("apps.appointments.views.send_email_async")
    def test_no_email_on_non_status_change(self, mock_send_email_async):
        """Updating symptoms without status change should not send email."""
        self._auth(self.staff_user)

        response = self.client.patch(
            f"/api/appointments/appointments/{self.appointment.id}/",
            {"symptoms": "Updated symptoms"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email_async.assert_not_called()


# ── Subscription & Billing Trigger Tests ─────────────────────────


class TrialExpiryWarningEmailTests(TestCase):
    """send_trial_expiry_warning() sends TRIAL_EXPIRY_WARNING email."""

    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Trial",
            slug="trial-warn",
            price=0,
            trial_days=14,
        )

    @patch("apps.subscriptions.tasks.send_email")
    def test_trial_warning_email_sent(self, mock_send_email):
        mock_send_email.return_value = True
        center = DiagnosticCenter.objects.create(
            name="Warning Center",
            domain="warning-center",
            email="admin@warning.com",
        )
        now = timezone.now()
        Subscription.objects.create(
            center=center,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            trial_start=now - timedelta(days=12),
            trial_end=now + timedelta(days=2),
        )

        from apps.subscriptions.tasks import send_trial_expiry_warning

        send_trial_expiry_warning()
        mock_send_email.assert_called_once()

        call_args = mock_send_email.call_args
        self.assertEqual(call_args.args[0], EmailType.TRIAL_EXPIRY_WARNING)
        self.assertEqual(call_args.kwargs["recipient"], "admin@warning.com")
        self.assertIn("days_left", call_args.kwargs["context"])


class TrialExpiredEmailTests(TestCase):
    """check_trial_expirations() sends TRIAL_EXPIRED email."""

    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name="Trial",
            slug="trial-exp",
            price=0,
            trial_days=14,
        )

    @patch("apps.subscriptions.tasks.send_email")
    def test_trial_expired_email_sent(self, mock_send_email):
        mock_send_email.return_value = True
        center = DiagnosticCenter.objects.create(
            name="Expired Center",
            domain="expired-center",
            email="admin@expired.com",
        )
        now = timezone.now()
        Subscription.objects.create(
            center=center,
            plan=self.plan,
            status=Subscription.Status.TRIAL,
            trial_start=now - timedelta(days=15),
            trial_end=now - timedelta(days=1),
        )

        from apps.subscriptions.tasks import check_trial_expirations

        check_trial_expirations()
        mock_send_email.assert_called_once()

        call_args = mock_send_email.call_args
        self.assertEqual(call_args.args[0], EmailType.TRIAL_EXPIRED)
        self.assertEqual(call_args.kwargs["recipient"], "admin@expired.com")


class InvoiceGeneratedEmailTests(TestCase):
    """generate_monthly_invoices() sends INVOICE_GENERATED email."""

    @patch("apps.subscriptions.tasks.send_email")
    def test_invoice_email_sent_on_generation(self, mock_send_email):
        mock_send_email.return_value = True
        plan = SubscriptionPlan.objects.create(
            name="Starter",
            slug="starter-inv",
            price=Decimal("2499"),
        )
        center = DiagnosticCenter.objects.create(
            name="Invoice Center",
            domain="invoice-center",
            email="billing@invoice.com",
        )
        Subscription.objects.create(
            center=center,
            plan=plan,
            status=Subscription.Status.ACTIVE,
            billing_date=timezone.now().date(),
        )

        from apps.subscriptions.tasks import generate_monthly_invoices

        generate_monthly_invoices()
        mock_send_email.assert_called_once()

        call_args = mock_send_email.call_args
        self.assertEqual(call_args.args[0], EmailType.INVOICE_GENERATED)
        self.assertEqual(call_args.kwargs["recipient"], "billing@invoice.com")
        ctx = call_args.kwargs["context"]
        self.assertIn("amount", ctx)
        self.assertIn("due_date", ctx)


class InvoiceOverdueEmailTests(TestCase):
    """mark_overdue_invoices() sends INVOICE_OVERDUE email."""

    @patch("apps.subscriptions.tasks.send_email")
    def test_overdue_email_sent(self, mock_send_email):
        mock_send_email.return_value = True
        plan = SubscriptionPlan.objects.create(
            name="Pro",
            slug="pro-overdue",
            price=Decimal("4999"),
        )
        center = DiagnosticCenter.objects.create(
            name="Overdue Center",
            domain="overdue-email",
            email="billing@overdue.com",
        )
        sub = Subscription.objects.create(
            center=center,
            plan=plan,
            status=Subscription.Status.ACTIVE,
        )
        Invoice.objects.create(
            subscription=sub,
            amount=Decimal("4999"),
            due_date=timezone.now().date() - timedelta(days=1),
            status=Invoice.Status.PENDING,
        )

        from apps.subscriptions.tasks import mark_overdue_invoices

        mark_overdue_invoices()
        mock_send_email.assert_called_once()

        call_args = mock_send_email.call_args
        self.assertEqual(call_args.args[0], EmailType.INVOICE_OVERDUE)
        self.assertEqual(call_args.kwargs["recipient"], "billing@overdue.com")


class PaymentReceivedEmailTests(TestCase):
    """SuperadminInvoiceMarkPaidView sends PAYMENT_RECEIVED email."""

    def setUp(self):
        from rest_framework.test import APIClient

        self.client = APIClient()
        self.superadmin = User.objects.create_superuser(
            username="pay_su",
            email="pay@super.com",
            password="admin123",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Starter",
            slug="starter-pay",
            price=Decimal("2499"),
        )
        self.center = DiagnosticCenter.objects.create(
            name="Payment Center",
            domain="payment-center",
            email="billing@payment.com",
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

    @patch("apps.subscriptions.views.send_email_async")
    def test_payment_received_email_on_mark_paid(self, mock_send_email_async):
        self.client.force_authenticate(self.superadmin)
        response = self.client.post(
            f"/api/subscriptions/invoices/{self.invoice.id}/mark-paid/",
            {"payment_method": "CASH"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email_async.assert_called_once()

        call_args = mock_send_email_async.call_args
        self.assertEqual(call_args.args[0], EmailType.PAYMENT_RECEIVED)
        self.assertEqual(call_args.kwargs["recipient"], "billing@payment.com")
        self.assertIn("amount", call_args.kwargs["context"])
        self.assertIn("plan_name", call_args.kwargs["context"])


# ── Admin Operation Trigger Tests ────────────────────────────────


class CenterCreatedEmailTests(TestCase):
    """SuperadminCenterCreateSerializer sends CENTER_CREATED email."""

    def setUp(self):
        from rest_framework.test import APIClient

        self.client = APIClient()
        self.superadmin = User.objects.create_superuser(
            username="center_su",
            email="center@super.com",
            password="admin123",
        )
        Permission.objects.get_or_create(
            codename="view_patients",
            defaults={"name": "View Patients", "category": "Patients"},
        )

    @patch("core.tenants.superadmin_serializers.send_email")
    def test_center_created_email_sent(self, mock_send_email):
        mock_send_email.return_value = True
        self.client.force_authenticate(self.superadmin)
        response = self.client.post(
            "/api/tenants/superadmin/centers/",
            {
                "name": "New Email Center",
                "domain": "new-email-center",
                "address": "123 Test St",
                "contact_number": "01700000001",
                "email": "info@newcenter.com",
                "admin_email": "admin@newcenter.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_send_email.assert_called_once()

        call_args = mock_send_email.call_args
        self.assertEqual(call_args.args[0], EmailType.CENTER_CREATED)
        self.assertEqual(call_args.kwargs["recipient"], "admin@newcenter.com")


class CenterDeactivatedEmailTests(TestCase):
    """SuperadminCenterToggleView sends CENTER_DEACTIVATED email."""

    def setUp(self):
        from rest_framework.test import APIClient

        self.client = APIClient()
        self.superadmin = User.objects.create_superuser(
            username="toggle_su",
            email="toggle@super.com",
            password="admin123",
        )
        self.center = DiagnosticCenter.objects.create(
            name="Toggle Center",
            domain="toggle-center",
            email="admin@toggle.com",
            is_active=True,
        )

    @patch("core.tenants.superadmin_views.send_email_async")
    def test_deactivation_sends_email(self, mock_send_email_async):
        self.client.force_authenticate(self.superadmin)
        response = self.client.post(
            f"/api/tenants/superadmin/centers/{self.center.id}/toggle-active/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_active"])
        mock_send_email_async.assert_called_once()

        call_args = mock_send_email_async.call_args
        self.assertEqual(call_args.args[0], EmailType.CENTER_DEACTIVATED)
        self.assertEqual(call_args.kwargs["recipient"], "admin@toggle.com")

    @patch("core.tenants.superadmin_views.send_email_async")
    def test_activation_does_not_send_email(self, mock_send_email_async):
        """Activating a center should NOT send deactivation email."""
        self.center.is_active = False
        self.center.save()

        self.client.force_authenticate(self.superadmin)
        response = self.client.post(
            f"/api/tenants/superadmin/centers/{self.center.id}/toggle-active/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_active"])
        mock_send_email_async.assert_not_called()


class AccountApprovalEmailTests(TestCase):
    """SuperadminUserDetailView sends ACCOUNT_APPROVED/DECLINED email."""

    def setUp(self):
        from rest_framework.test import APIClient

        self.client = APIClient()
        self.superadmin = User.objects.create_superuser(
            username="approval_su",
            email="approval@super.com",
            password="admin123",
        )
        self.center = make_center(name="Approval Center", domain="approval-center")
        self.pending_user = make_user(
            "pending_user",
            email="pending@test.com",
            first_name="Pending",
            last_name="User",
        )
        self.pending_user.center = self.center
        self.pending_user.approval_status = User.ApprovalStatus.PENDING
        self.pending_user.save()

    @patch("core.tenants.superadmin_views.send_email_async")
    def test_approval_sends_approved_email(self, mock_send_email_async):
        self.client.force_authenticate(self.superadmin)
        response = self.client.patch(
            f"/api/tenants/superadmin/users/{self.pending_user.id}/",
            {"approval_status": "APPROVED"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email_async.assert_called_once()

        call_args = mock_send_email_async.call_args
        self.assertEqual(call_args.args[0], EmailType.ACCOUNT_APPROVED)
        self.assertEqual(call_args.kwargs["recipient"], "pending@test.com")
        ctx = call_args.kwargs["context"]
        self.assertIn("patient_name", ctx)
        self.assertIn("center_name", ctx)
        self.assertIn("login_url", ctx)

    @patch("core.tenants.superadmin_views.send_email_async")
    def test_decline_sends_declined_email(self, mock_send_email_async):
        self.client.force_authenticate(self.superadmin)
        response = self.client.patch(
            f"/api/tenants/superadmin/users/{self.pending_user.id}/",
            {"approval_status": "DECLINED"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email_async.assert_called_once()

        call_args = mock_send_email_async.call_args
        self.assertEqual(call_args.args[0], EmailType.ACCOUNT_DECLINED)
        self.assertEqual(call_args.kwargs["recipient"], "pending@test.com")

    @patch("core.tenants.superadmin_views.send_email_async")
    def test_no_email_if_status_unchanged(self, mock_send_email_async):
        """Updating other fields without changing approval should not email."""
        self.client.force_authenticate(self.superadmin)
        response = self.client.patch(
            f"/api/tenants/superadmin/users/{self.pending_user.id}/",
            {"first_name": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email_async.assert_not_called()
