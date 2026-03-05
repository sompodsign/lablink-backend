import logging

from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import permissions, viewsets

from core.tenants.permissions import IsCenterStaff

from .models import Payment
from .serializers import PaymentCreateSerializer, PaymentSerializer

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        tags=['Payments'],
        summary='List payments',
        description=(
            'Returns all payments for appointments at the current center, '
            'ordered by most recent first. Staff only.'
        ),
    ),
    retrieve=extend_schema(
        tags=['Payments'],
        summary='Get payment detail',
    ),
    create=extend_schema(
        tags=['Payments'],
        summary='Record a payment',
        description=(
            'Staff records a payment for an appointment, optionally linked to a specific test order. '
            'The appointment must belong to the current center.'
        ),
        request=PaymentCreateSerializer,
        responses={201: PaymentSerializer},
        examples=[
            OpenApiExample(
                'Cash payment for appointment',
                value={
                    'appointment': 1,
                    'amount': '1500.00',
                    'method': 'CASH',
                    'status': 'COMPLETED',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Mobile banking payment for specific test',
                value={
                    'appointment': 1,
                    'test_order': 3,
                    'amount': '800.00',
                    'method': 'MOBILE_BANKING',
                    'transaction_id': 'BKS20260305001',
                    'status': 'COMPLETED',
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=['Payments'],
        summary='Update payment status',
        description='Update payment status (e.g., mark a pending payment as completed or failed).',
    ),
)
class PaymentViewSet(viewsets.ModelViewSet):
    """
    Payment recording and listing for the current tenant center.
    Strictly scoped to staff only.
    """

    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    permission_classes = [permissions.IsAuthenticated, IsCenterStaff]

    def get_queryset(self):
        tenant = self.request.tenant
        return Payment.objects.filter(
            appointment__center=tenant,
        ).select_related(
            'appointment__patient',
            'test_order__test_type',
        ).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer
