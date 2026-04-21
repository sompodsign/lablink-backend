"""
UddoktaPay gateway views for subscription invoices.

* ``SubscriptionInitiateChargeView``  – center admin initiates a charge.
* ``SubscriptionVerifyPaymentView``   – callback after customer returns.
"""

import logging
from urllib.parse import urlparse, urlunparse

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments import uddoktapay_client as gateway
from core.tenants.permissions import IsCenterAdmin

from .models import Invoice
from .services import apply_successful_invoice_payment, apply_credit_to_invoice

logger = logging.getLogger(__name__)


def _is_local_host(hostname: str) -> bool:
    return hostname == "localhost" or hostname.endswith(".localhost")


def _normalize_return_url(request, raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme and parsed.netloc and not _is_local_host(parsed.hostname or ""):
        return raw_url

    request_scheme = "https" if request.is_secure() else "http"
    request_origin = urlparse(f"{request_scheme}://{request.get_host()}")
    request_is_local = _is_local_host(request_origin.hostname or "")

    origin = request.META.get("HTTP_ORIGIN", "") or getattr(
        settings, "FRONTEND_URL", ""
    )
    origin_parsed = urlparse(origin)
    origin_is_usable = bool(origin_parsed.scheme and origin_parsed.netloc)
    origin_is_local = _is_local_host(origin_parsed.hostname or "")

    if not origin_is_usable:
        origin_parsed = request_origin
    elif origin_is_local and not request_is_local:
        origin_parsed = request_origin

    return urlunparse(
        (
            origin_parsed.scheme,
            origin_parsed.netloc,
            parsed.path or "/dashboard/subscription",
            "",
            parsed.query,
            parsed.fragment,
        )
    )


class SubscriptionInitiateChargeView(APIView):
    """Center admin: initiate UddoktaPay charge for a subscription invoice."""

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def post(self, request):
        tenant = request.tenant
        if not tenant:
            return Response(
                {"detail": "No center context."},
                status=status.HTTP_404_NOT_FOUND,
            )

        invoice_id = request.data.get("invoice_id")
        redirect_url = request.data.get("redirect_url")

        if not invoice_id:
            return Response(
                {"detail": "invoice_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not redirect_url:
            return Response(
                {"detail": "redirect_url is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            invoice = Invoice.objects.select_related(
                "subscription__center",
            ).get(
                pk=invoice_id,
                subscription__center=tenant,
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

        # Apply credit balance if available
        center = invoice.subscription.center
        invoice, fully_paid = apply_credit_to_invoice(invoice, center)
        if fully_paid:
            return Response(
                {
                    "status": "COMPLETED",
                    "detail": "Paid using credit balance. Subscription activated.",
                    "transaction_id": None,
                },
            )

        # Build charge payload
        full_name = center.name or "Customer"
        email = center.email or request.user.email or "noreply@lablink.bd"

        metadata = {
            "subscription_invoice_id": str(invoice.pk),
            "center_id": str(tenant.pk),
            "type": "subscription",
        }

        try:
            result = gateway.create_charge(
                full_name=full_name,
                email=email,
                amount=str(invoice.amount),
                redirect_url=_normalize_return_url(request, redirect_url),
                cancel_url=_normalize_return_url(
                    request,
                    request.data.get("cancel_url") or redirect_url,
                ),
                metadata=metadata,
            )
        except gateway.UddoktaPayError as exc:
            logger.exception("UddoktaPay create_charge error for subscription")
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "payment_url": result.payment_url,
                "invoice_id": invoice.pk,
            },
            status=status.HTTP_201_CREATED,
        )


class SubscriptionVerifyPaymentView(APIView):
    """Callback after customer returns from UddoktaPay for subscription."""

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def get(self, request):
        if not request.tenant:
            return Response(
                {"detail": "No center context."},
                status=status.HTTP_404_NOT_FOUND,
            )

        gw_invoice_id = request.query_params.get("invoice_id")
        if not gw_invoice_id:
            return Response(
                {"detail": "invoice_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = gateway.verify_payment(invoice_id=gw_invoice_id)
        except gateway.UddoktaPayError as exc:
            logger.exception("UddoktaPay verify_payment error for subscription")
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Find the local subscription invoice from metadata
        metadata = result.metadata or {}
        sub_invoice_id = metadata.get("subscription_invoice_id")
        metadata_center_id = metadata.get("center_id")
        if not sub_invoice_id:
            return Response(
                {"detail": "subscription_invoice_id missing from metadata."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not metadata_center_id:
            return Response(
                {"detail": "center_id missing from metadata."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if str(request.tenant.pk) != str(metadata_center_id):
            return Response(
                {"detail": "Payment does not belong to this center."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            invoice = Invoice.objects.select_related(
                "subscription__center",
            ).get(pk=sub_invoice_id, subscription__center=request.tenant)
        except Invoice.DoesNotExist:
            return Response(
                {"detail": "Subscription invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Store gateway info on the invoice
        invoice.gateway_invoice_id = result.invoice_id
        invoice.transaction_id = result.transaction_id

        if result.status == "COMPLETED":
            invoice, sub = apply_successful_invoice_payment(
                invoice,
                payment_method=Invoice.PaymentMethod.ONLINE,
                transaction_id=result.transaction_id,
                gateway_invoice_id=result.invoice_id,
            )

            logger.info(
                "Subscription invoice #%s paid via gateway for %s",
                invoice.pk,
                sub.center.name,
            )

            return Response(
                {
                    "status": "COMPLETED",
                    "detail": "Payment verified. Subscription activated.",
                    "transaction_id": result.transaction_id,
                }
            )
        else:
            invoice.save(
                update_fields=[
                    "transaction_id",
                    "gateway_invoice_id",
                ]
            )
            return Response(
                {
                    "status": result.status,
                    "detail": f"Payment status: {result.status}",
                }
            )
