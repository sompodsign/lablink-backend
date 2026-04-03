"""
UddoktaPay gateway views.

* ``InitiateChargeView``  – staff creates a charge for an invoice.
* ``VerifyPaymentView``   – redirect-callback that verifies via API.
* ``WebhookView``         – server-to-server webhook from UddoktaPay.
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.tenants.permissions import IsCenterStaff

from . import uddoktapay_client as gateway
from .gateway_serializers import ChargeResponseSerializer, InitiateChargeSerializer
from .models import Invoice, Payment

logger = logging.getLogger(__name__)


class InitiateChargeView(APIView):
    """
    Create a UddoktaPay charge for a local Invoice.

    Returns the ``payment_url`` that the frontend should redirect
    the customer to.
    """

    permission_classes = [permissions.IsAuthenticated, IsCenterStaff]

    @extend_schema(
        tags=["Payments"],
        summary="Initiate online payment",
        request=InitiateChargeSerializer,
        responses={201: ChargeResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        ser = InitiateChargeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        tenant = request.tenant

        # ── Fetch the invoice ──────────────────────────────────
        try:
            invoice = Invoice.objects.get(
                pk=ser.validated_data["invoice_id"],
                center=tenant,
            )
        except Invoice.DoesNotExist:
            return Response(
                {"detail": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if invoice.status == Invoice.Status.PAID:
            return Response(
                {"detail": "Invoice is already paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Determine full_name / email ────────────────────────
        if invoice.patient:
            full_name = invoice.patient.get_full_name() or "Customer"
            email = invoice.patient.email or "noreply@lablink.bd"
        else:
            full_name = invoice.walk_in_name or "Walk-in Customer"
            email = "noreply@lablink.bd"

        if not invoice.appointment_id:
            return Response(
                {
                    "detail": "Online payments for walk-in invoices (no appointment) are not supported yet."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Create a PENDING Payment record ────────────────────
        payment = Payment.objects.create(
            appointment_id=invoice.appointment_id,
            invoice=invoice,
            amount=invoice.total,
            method=Payment.Method.ONLINE,
            status=Payment.Status.PENDING,
        )

        # ── Call UddoktaPay ────────────────────────────────────
        metadata = {
            "payment_id": str(payment.pk),
            "invoice_id": str(invoice.pk),
            "center_id": str(tenant.pk),
        }

        try:
            result = gateway.create_charge(
                full_name=full_name,
                email=email,
                amount=str(invoice.total),
                redirect_url=ser.validated_data["redirect_url"],
                cancel_url=ser.validated_data.get("cancel_url", ""),
                webhook_url="",  # can be set later when publicly hosted
                metadata=metadata,
            )
        except gateway.UddoktaPayError as exc:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            logger.exception("UddoktaPay create_charge error")
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        out = ChargeResponseSerializer(
            {"payment_url": result.payment_url, "payment_id": payment.pk}
        )
        return Response(out.data, status=status.HTTP_201_CREATED)


class VerifyPaymentView(APIView):
    """
    Callback endpoint hit after the customer returns from UddoktaPay.

    Receives ``invoice_id`` (UddoktaPay's, not ours) as a query
    parameter, calls the Verify Payment API, and updates the local
    Payment record accordingly.
    """

    permission_classes = [permissions.IsAuthenticated, IsCenterStaff]

    @extend_schema(
        tags=["Payments"],
        summary="Verify online payment status",
        description=(
            "Called after the customer returns from UddoktaPay. "
            "Pass `invoice_id` (gateway) as a query parameter."
        ),
    )
    def get(self, request: Request) -> Response:
        invoice_id = request.query_params.get("invoice_id")
        if not invoice_id:
            return Response(
                {"detail": "invoice_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = gateway.verify_payment(invoice_id=invoice_id)
        except gateway.UddoktaPayError as exc:
            logger.exception("UddoktaPay verify_payment error")
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # ── Find local Payment via metadata ────────────────────
        payment_id = result.metadata.get("payment_id")
        if not payment_id:
            return Response(
                {"detail": "payment_id missing from gateway metadata."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = Payment.objects.get(pk=payment_id)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Map gateway status → local status ──────────────────
        status_map = {
            "COMPLETED": Payment.Status.COMPLETED,
            "PENDING": Payment.Status.PENDING,
        }
        payment.status = status_map.get(result.status, Payment.Status.FAILED)
        payment.gateway_invoice_id = result.invoice_id
        payment.transaction_id = result.transaction_id
        payment.gateway_response = {
            "payment_method": result.payment_method,
            "sender_number": result.sender_number,
            "fee": result.fee,
            "charged_amount": result.charged_amount,
            "date": result.date,
        }
        payment.save(
            update_fields=[
                "status",
                "gateway_invoice_id",
                "transaction_id",
                "gateway_response",
            ]
        )

        # Also update invoice status when payment is completed
        if payment.status == Payment.Status.COMPLETED and payment.invoice:
            from django.utils import timezone

            payment.invoice.status = Invoice.Status.PAID
            payment.invoice.paid_at = timezone.now()
            payment.invoice.save(update_fields=["status", "paid_at"])

        return Response(
            {
                "status": payment.status,
                "transaction_id": payment.transaction_id,
                "payment_method": result.payment_method,
                "amount": result.amount,
            }
        )


class WebhookView(APIView):
    """
    Server-to-server webhook from UddoktaPay.

    UddoktaPay sends the same payload as Verify Payment to
    this endpoint every time a payment status changes.  We
    validate the ``RT-UDDOKTAPAY-API-KEY`` header and update
    the local Payment accordingly.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Payments"],
        summary="UddoktaPay webhook (server-to-server)",
        description="Called by UddoktaPay when payment status changes.",
    )
    def post(self, request: Request) -> Response:
        from django.conf import settings as django_settings

        # ── Validate API key header ────────────────────────────
        header_key = request.META.get("HTTP_RT_UDDOKTAPAY_API_KEY", "")
        if header_key != django_settings.UDDOKTAPAY_API_KEY:
            return Response(
                {"detail": "Unauthorized."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = request.data
        payment_id = (data.get("metadata") or {}).get("payment_id")
        if not payment_id:
            return Response(
                {"detail": "payment_id missing from metadata."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = Payment.objects.get(pk=payment_id)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        status_map = {
            "COMPLETED": Payment.Status.COMPLETED,
            "PENDING": Payment.Status.PENDING,
        }
        payment.status = status_map.get(data.get("status", ""), Payment.Status.FAILED)
        payment.gateway_invoice_id = data.get("invoice_id", "")
        payment.transaction_id = data.get("transaction_id", "")
        payment.gateway_response = {
            "payment_method": data.get("payment_method", ""),
            "sender_number": data.get("sender_number", ""),
            "fee": data.get("fee", ""),
            "charged_amount": data.get("charged_amount", ""),
            "date": data.get("date", ""),
        }
        payment.save(
            update_fields=[
                "status",
                "gateway_invoice_id",
                "transaction_id",
                "gateway_response",
            ]
        )

        if payment.status == Payment.Status.COMPLETED and payment.invoice:
            from django.utils import timezone

            payment.invoice.status = Invoice.Status.PAID
            payment.invoice.paid_at = timezone.now()
            payment.invoice.save(update_fields=["status", "paid_at"])

        logger.info(
            "Webhook processed: payment=%s status=%s", payment.pk, payment.status
        )
        return Response({"detail": "OK"}, status=status.HTTP_200_OK)
