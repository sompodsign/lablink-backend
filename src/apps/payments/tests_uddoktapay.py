"""
Unit tests for UddoktaPay gateway integration.

* ``UddoktaPayClientTests`` – tests the client module with mocked HTTP.
* ``GatewayViewTests``       – tests the API views end-to-end (mock gateway).
"""

import logging
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.payments.models import Invoice, Payment
from apps.payments.uddoktapay_client import (
    CheckoutResult,
    UddoktaPayError,
    VerifyResult,
    create_charge,
    verify_payment,
)
from helpers.test_factories import (
    jwt_auth_header,
    make_appointment,
    make_center,
    make_patient,
    make_staff,
    make_user,
)

logger = logging.getLogger(__name__)


# ─── Client Tests ────────────────────────────────────────────────


@override_settings(
    UDDOKTAPAY_BASE_URL="https://sandbox.uddoktapay.com",
    UDDOKTAPAY_API_KEY="test-api-key-123",
)
class UddoktaPayClientTests(TestCase):
    """Unit tests for ``uddoktapay_client`` functions."""

    @patch("apps.payments.uddoktapay_client.requests.post")
    def test_create_charge_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": True,
            "message": "Payment Url",
            "payment_url": "https://sandbox.uddoktapay.com/payment/abc123",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = create_charge(
            full_name="John Doe",
            email="john@example.com",
            amount="500",
            redirect_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )

        self.assertIsInstance(result, CheckoutResult)
        self.assertTrue(result.status)
        self.assertEqual(
            result.payment_url,
            "https://sandbox.uddoktapay.com/payment/abc123",
        )

        # Verify the POST was called correctly
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        self.assertEqual(
            call_kwargs.kwargs["headers"]["RT-UDDOKTAPAY-API-KEY"],
            "test-api-key-123",
        )

    @patch("apps.payments.uddoktapay_client.requests.post")
    def test_create_charge_api_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": False,
            "message": "Invalid amount",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        with self.assertRaises(UddoktaPayError) as ctx:
            create_charge(
                full_name="John",
                email="john@test.com",
                amount="0",
                redirect_url="https://example.com/success",
            )
        self.assertIn("Invalid amount", str(ctx.exception))

    @patch("apps.payments.uddoktapay_client.requests.post")
    def test_create_charge_network_error(self, mock_post):
        import requests

        mock_post.side_effect = requests.ConnectionError("Connection refused")

        with self.assertRaises(UddoktaPayError) as ctx:
            create_charge(
                full_name="John",
                email="john@test.com",
                amount="100",
                redirect_url="https://example.com/success",
            )
        self.assertIn("Network error", str(ctx.exception))

    @patch("apps.payments.uddoktapay_client.requests.post")
    def test_verify_payment_completed(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "full_name": "John Doe",
            "email": "john@example.com",
            "amount": "500.00",
            "fee": "0.00",
            "charged_amount": "500.00",
            "invoice_id": "Erm9wzjM0FBwjSYT0QVb",
            "metadata": {"payment_id": "1", "invoice_id": "2"},
            "payment_method": "bkash",
            "sender_number": "01311111111",
            "transaction_id": "TXN123",
            "date": "2023-01-07 14:00:50",
            "status": "COMPLETED",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = verify_payment(invoice_id="Erm9wzjM0FBwjSYT0QVb")

        self.assertIsInstance(result, VerifyResult)
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.transaction_id, "TXN123")
        self.assertEqual(result.payment_method, "bkash")

    @patch("apps.payments.uddoktapay_client.requests.post")
    def test_verify_payment_error_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": "Invoice not found",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        with self.assertRaises(UddoktaPayError) as ctx:
            verify_payment(invoice_id="invalid-id")
        self.assertIn("Invoice not found", str(ctx.exception))


# ─── View Tests ──────────────────────────────────────────────────


@override_settings(
    UDDOKTAPAY_BASE_URL="https://sandbox.uddoktapay.com",
    UDDOKTAPAY_API_KEY="test-api-key-123",
)
class GatewayViewTests(APITestCase):
    """End-to-end API tests for gateway views with mocked UddoktaPay calls."""

    def setUp(self):
        self.center = make_center()
        self.staff_user = make_user("gw_staff")
        make_staff(self.staff_user, self.center, "Admin")
        self.patient = make_patient("gw_patient", self.center)
        self.appt = make_appointment(self.patient, self.center)

        # Create an invoice
        self.invoice = Invoice.objects.create(
            patient=self.patient,
            center=self.center,
            appointment=self.appt,
            subtotal=Decimal("1000.00"),
            total=Decimal("1000.00"),
            status=Invoice.Status.ISSUED,
        )

    def _auth(self, user=None):
        user = user or self.staff_user
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    # ── Initiate Charge ────────────────────────────────────────

    @patch("apps.payments.gateway_views.gateway.create_charge")
    def test_initiate_charge_success(self, mock_create):
        mock_create.return_value = CheckoutResult(
            status=True,
            message="Payment Url",
            payment_url="https://sandbox.uddoktapay.com/payment/abc123",
        )
        self._auth()
        resp = self.client.post(
            "/api/payments/gateway/initiate-charge/",
            {
                "invoice_id": self.invoice.pk,
                "redirect_url": "https://example.com/success",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("payment_url", resp.data)
        self.assertIn("payment_id", resp.data)

        # Verify a Payment record was created
        payment = Payment.objects.get(pk=resp.data["payment_id"])
        self.assertEqual(payment.method, Payment.Method.ONLINE)
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.amount, Decimal("1000.00"))

    @patch("apps.payments.gateway_views.gateway.create_charge")
    def test_initiate_charge_gateway_error(self, mock_create):
        mock_create.side_effect = UddoktaPayError("Gateway timeout")
        self._auth()
        resp = self.client.post(
            "/api/payments/gateway/initiate-charge/",
            {
                "invoice_id": self.invoice.pk,
                "redirect_url": "https://example.com/success",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)

        # Payment should be marked FAILED
        payment = Payment.objects.filter(invoice=self.invoice).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, Payment.Status.FAILED)

    def test_initiate_charge_already_paid(self):
        self.invoice.status = Invoice.Status.PAID
        self.invoice.save()
        self._auth()
        resp = self.client.post(
            "/api/payments/gateway/initiate-charge/",
            {
                "invoice_id": self.invoice.pk,
                "redirect_url": "https://example.com/success",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_initiate_charge_invoice_not_found(self):
        self._auth()
        resp = self.client.post(
            "/api/payments/gateway/initiate-charge/",
            {
                "invoice_id": 99999,
                "redirect_url": "https://example.com/success",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ── Verify Payment ─────────────────────────────────────────

    @patch("apps.payments.gateway_views.gateway.verify_payment")
    def test_verify_payment_completed(self, mock_verify):
        # Create a pending payment first
        payment = Payment.objects.create(
            appointment=self.appt,
            invoice=self.invoice,
            amount=Decimal("1000.00"),
            method=Payment.Method.ONLINE,
            status=Payment.Status.PENDING,
        )
        mock_verify.return_value = VerifyResult(
            full_name="John Doe",
            email="john@example.com",
            amount="1000.00",
            fee="0.00",
            charged_amount="1000.00",
            invoice_id="GW-INV-123",
            metadata={"payment_id": str(payment.pk)},
            payment_method="bkash",
            sender_number="01711111111",
            transaction_id="TXN456",
            date="2025-01-07 14:00:50",
            status="COMPLETED",
        )
        self._auth()
        resp = self.client.get(
            "/api/payments/gateway/verify-payment/",
            {"invoice_id": "GW-INV-123"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "COMPLETED")
        self.assertEqual(resp.data["transaction_id"], "TXN456")

        # Payment record should be updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.COMPLETED)
        self.assertEqual(payment.gateway_invoice_id, "GW-INV-123")
        self.assertEqual(payment.transaction_id, "TXN456")

        # Invoice should also become PID
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        self.assertIsNotNone(self.invoice.paid_at)

    def test_verify_payment_missing_invoice_id(self):
        self._auth()
        resp = self.client.get("/api/payments/gateway/verify-payment/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Webhook ────────────────────────────────────────────────

    def test_webhook_success(self):
        payment = Payment.objects.create(
            appointment=self.appt,
            invoice=self.invoice,
            amount=Decimal("1000.00"),
            method=Payment.Method.ONLINE,
            status=Payment.Status.PENDING,
        )
        resp = self.client.post(
            "/api/payments/gateway/webhook/",
            data={
                "full_name": "John Doe",
                "email": "john@example.com",
                "amount": "1000.00",
                "fee": "0.00",
                "charged_amount": "1000.00",
                "invoice_id": "GW-INV-789",
                "metadata": {"payment_id": str(payment.pk)},
                "payment_method": "nagad",
                "sender_number": "01811111111",
                "transaction_id": "TXN789",
                "date": "2025-01-07 15:00:00",
                "status": "COMPLETED",
            },
            format="json",
            HTTP_RT_UDDOKTAPAY_API_KEY="test-api-key-123",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.COMPLETED)
        self.assertEqual(payment.gateway_invoice_id, "GW-INV-789")
        self.assertEqual(payment.transaction_id, "TXN789")

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)

    def test_webhook_unauthorized(self):
        resp = self.client.post(
            "/api/payments/gateway/webhook/",
            data={"status": "COMPLETED"},
            format="json",
            HTTP_RT_UDDOKTAPAY_API_KEY="wrong-key",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_webhook_missing_metadata(self):
        resp = self.client.post(
            "/api/payments/gateway/webhook/",
            data={
                "status": "COMPLETED",
                "metadata": {},
            },
            format="json",
            HTTP_RT_UDDOKTAPAY_API_KEY="test-api-key-123",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
