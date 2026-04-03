"""
UddoktaPay gateway views for subscription invoices.

* ``SubscriptionInitiateChargeView``  – center admin initiates a charge.
* ``SubscriptionVerifyPaymentView``   – callback after customer returns.
"""

import logging

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments import uddoktapay_client as gateway
from core.tenants.permissions import IsCenterAdmin

from .models import Invoice, Subscription

logger = logging.getLogger(__name__)


class SubscriptionInitiateChargeView(APIView):
    """Center admin: initiate UddoktaPay charge for a subscription invoice."""

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def post(self, request):
        tenant = request.tenant
        if not tenant:
            return Response(
                {'detail': 'No center context.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        invoice_id = request.data.get('invoice_id')
        redirect_url = request.data.get('redirect_url')

        if not invoice_id:
            return Response(
                {'detail': 'invoice_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not redirect_url:
            return Response(
                {'detail': 'redirect_url is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            invoice = Invoice.objects.select_related(
                'subscription__center',
            ).get(
                pk=invoice_id,
                subscription__center=tenant,
            )
        except Invoice.DoesNotExist:
            return Response(
                {'detail': 'Invoice not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if invoice.status == Invoice.Status.PAID:
            return Response(
                {'detail': 'Invoice is already paid.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build charge payload
        center = invoice.subscription.center
        full_name = center.name or 'Customer'
        email = center.email or request.user.email or 'noreply@lablink.bd'

        metadata = {
            'subscription_invoice_id': str(invoice.pk),
            'center_id': str(tenant.pk),
            'type': 'subscription',
        }

        try:
            result = gateway.create_charge(
                full_name=full_name,
                email=email,
                amount=str(invoice.amount),
                redirect_url=redirect_url,
                cancel_url=request.data.get('cancel_url', ''),
                metadata=metadata,
            )
        except gateway.UddoktaPayError as exc:
            logger.exception('UddoktaPay create_charge error for subscription')
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                'payment_url': result.payment_url,
                'invoice_id': invoice.pk,
            },
            status=status.HTTP_201_CREATED,
        )


class SubscriptionVerifyPaymentView(APIView):
    """Callback after customer returns from UddoktaPay for subscription."""

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def get(self, request):
        gw_invoice_id = request.query_params.get('invoice_id')
        if not gw_invoice_id:
            return Response(
                {'detail': 'invoice_id query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = gateway.verify_payment(invoice_id=gw_invoice_id)
        except gateway.UddoktaPayError as exc:
            logger.exception('UddoktaPay verify_payment error for subscription')
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Find the local subscription invoice from metadata
        sub_invoice_id = (result.metadata or {}).get('subscription_invoice_id')
        if not sub_invoice_id:
            return Response(
                {'detail': 'subscription_invoice_id missing from metadata.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            invoice = Invoice.objects.select_related(
                'subscription',
            ).get(pk=sub_invoice_id)
        except Invoice.DoesNotExist:
            return Response(
                {'detail': 'Subscription invoice not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Store gateway info on the invoice
        invoice.gateway_invoice_id = result.invoice_id
        invoice.transaction_id = result.transaction_id

        if result.status == 'COMPLETED':
            invoice.status = Invoice.Status.PAID
            invoice.paid_at = timezone.now()
            invoice.payment_method = Invoice.PaymentMethod.ONLINE
            invoice.save(update_fields=[
                'status', 'paid_at', 'payment_method',
                'transaction_id', 'gateway_invoice_id',
            ])

            # Apply plan upgrade and activate subscription
            sub = invoice.subscription
            if invoice.target_plan:
                sub.plan = invoice.target_plan
            sub.status = Subscription.Status.ACTIVE
            sub.save(update_fields=['status', 'plan'])

            # Invalidate cache
            from django.core.cache import cache
            cache.delete(f'sub_status:{sub.center_id}')

            logger.info(
                'Subscription invoice #%s paid via gateway for %s',
                invoice.pk,
                sub.center.name,
            )

            return Response({
                'status': 'COMPLETED',
                'detail': 'Payment verified. Subscription activated.',
                'transaction_id': result.transaction_id,
            })
        else:
            invoice.save(update_fields=[
                'transaction_id', 'gateway_invoice_id',
            ])
            return Response({
                'status': result.status,
                'detail': f'Payment status: {result.status}',
            })
