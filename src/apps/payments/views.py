import logging

from rest_framework import permissions, viewsets

from core.tenants.permissions import IsCenterStaff

from .models import Payment
from .serializers import PaymentCreateSerializer, PaymentSerializer

logger = logging.getLogger(__name__)


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
