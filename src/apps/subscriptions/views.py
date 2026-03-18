import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.tenants.permissions import IsCenterAdmin, IsSuperAdmin

from .models import Invoice, Subscription, SubscriptionPlan
from .serializers import (
    CenterRegistrationSerializer,
    InvoiceSerializer,
    SubscriptionPlanSerializer,
    SubscriptionSerializer,
)

logger = logging.getLogger(__name__)


# ── Public Views ─────────────────────────────────────────────────


class PublicPlanListView(APIView):
    """Public: list available subscription plans."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)


class CenterRegistrationView(APIView):
    """Public: register a new diagnostic center with subscription."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = CenterRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        center = result['center']
        subscription = result['subscription']

        response_data = {
            'detail': 'Center registered successfully!',
            'center': {
                'id': center.id,
                'name': center.name,
                'domain': center.domain,
            },
            'subscription': {
                'plan': subscription.plan.name,
                'status': subscription.status,
                'trial_end': (
                    subscription.trial_end.isoformat()
                    if subscription.trial_end
                    else None
                ),
            },
            'admin': {
                'username': result['admin_user'].username,
                'email': result['admin_user'].email,
            },
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


# ── Center Admin Views ───────────────────────────────────────────


class CenterSubscriptionView(APIView):
    """Center admin: view own subscription details."""

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def get(self, request):
        tenant = request.tenant
        if not tenant:
            return Response(
                {'detail': 'No center context.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            subscription = Subscription.objects.select_related('plan').get(
                center=tenant,
            )
        except Subscription.DoesNotExist:
            return Response(
                {'detail': 'No subscription found for this center.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)


class SubscriptionStatusView(APIView):
    """Any authenticated user: check subscription status for their center."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = request.tenant
        if not tenant:
            return Response(
                {'status': 'NONE', 'is_blocked': False},
            )

        from django.core.cache import cache

        cache_key = f'sub_status:{tenant.id}'
        cached = cache.get(cache_key)

        if cached:
            sub_status = cached
        else:
            try:
                sub = Subscription.objects.filter(center=tenant).latest(
                    'started_at',
                )
                sub_status = sub.status
            except Subscription.DoesNotExist:
                sub_status = 'NONE'
            cache.set(cache_key, sub_status, 300)

        is_blocked = sub_status in ('EXPIRED', 'CANCELLED')

        return Response({
            'status': sub_status,
            'is_blocked': is_blocked,
            'center_name': tenant.name,
        })


# ── Superadmin Views ─────────────────────────────────────────────


class SuperadminSubscriptionListView(APIView):
    """Superadmin: list all subscriptions across centers."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        subscriptions = (
            Subscription.objects.select_related('plan', 'center')
            .prefetch_related('invoices')
            .order_by('-started_at')
        )

        # Optional filters
        status_filter = request.query_params.get('status')
        if status_filter:
            subscriptions = subscriptions.filter(status=status_filter.upper())

        search = request.query_params.get('search', '').strip()
        if search:
            subscriptions = subscriptions.filter(
                center__name__icontains=search,
            )

        data = []
        for sub in subscriptions[:100]:
            data.append({  # noqa: PERF401
                'id': sub.id,
                'center_id': sub.center.id,
                'center_name': sub.center.name,
                'center_domain': sub.center.domain,
                'plan_name': sub.plan.name,
                'plan_price': str(sub.plan.price),
                'status': sub.status,
                'trial_start': (
                    sub.trial_start.isoformat() if sub.trial_start else None
                ),
                'trial_end': sub.trial_end.isoformat() if sub.trial_end else None,
                'billing_date': (
                    sub.billing_date.isoformat() if sub.billing_date else None
                ),
                'started_at': sub.started_at.isoformat(),
                'invoices_count': sub.invoices.count(),
                'pending_invoices': sub.invoices.filter(
                    status=Invoice.Status.PENDING,
                ).count(),
            })

        return Response(data)


class SuperadminInvoiceListView(APIView):
    """Superadmin: list invoices with filters."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        invoices = Invoice.objects.select_related(
            'subscription__center',
            'subscription__plan',
        ).order_by('-created_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            invoices = invoices.filter(status=status_filter.upper())

        center_id = request.query_params.get('center')
        if center_id:
            invoices = invoices.filter(
                subscription__center_id=center_id,
            )

        data = []
        for inv in invoices[:100]:
            data.append({  # noqa: PERF401
                'id': inv.id,
                'center_name': inv.subscription.center.name,
                'center_domain': inv.subscription.center.domain,
                'plan_name': inv.subscription.plan.name,
                'amount': str(inv.amount),
                'status': inv.status,
                'payment_method': inv.payment_method,
                'due_date': inv.due_date.isoformat(),
                'paid_at': inv.paid_at.isoformat() if inv.paid_at else None,
                'transaction_id': inv.transaction_id,
                'notes': inv.notes,
                'created_at': inv.created_at.isoformat(),
            })

        return Response(data)


class SuperadminInvoiceMarkPaidView(APIView):
    """Superadmin: mark an invoice as paid and activate subscription."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request, invoice_id):
        try:
            invoice = Invoice.objects.select_related(
                'subscription',
            ).get(pk=invoice_id)
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

        from django.utils import timezone

        # Update invoice
        invoice.status = Invoice.Status.PAID
        invoice.paid_at = timezone.now()
        invoice.payment_method = request.data.get(
            'payment_method', invoice.payment_method
        )
        invoice.transaction_id = request.data.get(
            'transaction_id', invoice.transaction_id
        )
        invoice.notes = request.data.get('notes', invoice.notes)
        invoice.save()

        # Activate subscription
        sub = invoice.subscription
        sub.status = Subscription.Status.ACTIVE
        sub.save(update_fields=['status'])

        logger.info(
            'Invoice #%s marked paid by superadmin %s',
            invoice.id,
            request.user.username,
        )

        return Response({
            'detail': f'Invoice #{invoice.id} marked as paid. Subscription activated.',
            'invoice': InvoiceSerializer(invoice).data,
        })


class SuperadminInvoiceMarkUnpaidView(APIView):
    """Superadmin: revert a paid invoice back to pending."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request, invoice_id):
        try:
            invoice = Invoice.objects.select_related(
                'subscription',
            ).get(pk=invoice_id)
        except Invoice.DoesNotExist:
            return Response(
                {'detail': 'Invoice not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if invoice.status != Invoice.Status.PAID:
            return Response(
                {'detail': 'Invoice is not paid.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Revert invoice
        invoice.status = Invoice.Status.PENDING
        invoice.paid_at = None
        invoice.save(update_fields=['status', 'paid_at'])

        logger.info(
            'Invoice #%s reverted to unpaid by superadmin %s',
            invoice.id,
            request.user.username,
        )

        return Response({
            'detail': f'Invoice #{invoice.id} reverted to pending.',
            'invoice': InvoiceSerializer(invoice).data,
        })
