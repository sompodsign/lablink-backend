import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.tenants.permissions import (
    IsCenterDoctor,
    IsCenterLabTechnician,
    IsCenterStaff,
    IsCenterStaffOrDoctor,
    IsPatientOwner,
)

from .models import CenterTestPricing, Report, TestOrder, TestType
from .serializers import (
    CenterTestPricingSerializer,
    ReportCreateSerializer,
    ReportSerializer,
    TestOrderCreateSerializer,
    TestOrderSerializer,
    TestOrderStatusUpdateSerializer,
    TestTypeSerializer,
)

logger = logging.getLogger(__name__)


class TestTypeViewSet(viewsets.ModelViewSet):
    serializer_class = TestTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return TestType.objects.all()


class CenterTestPricingViewSet(viewsets.ModelViewSet):
    serializer_class = CenterTestPricingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        tenant = self.request.tenant
        return CenterTestPricing.objects.filter(center=tenant).select_related('test_type')


class TestOrderViewSet(viewsets.ModelViewSet):
    """
    Doctors create test orders; lab technicians and staff manage them.
    Strictly scoped to the current tenant center.
    """

    def get_queryset(self):
        tenant = self.request.tenant
        qs = TestOrder.objects.filter(center=tenant).select_related(
            'test_type',
            'appointment__patient',
            'ordered_by',
        )
        # Optional status filter
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return TestOrderCreateSerializer
        if self.action in ('partial_update', 'update') and not IsCenterDoctor().has_permission(
            self.request, self
        ):
            return TestOrderStatusUpdateSerializer
        return TestOrderSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsCenterDoctor()]
        if self.action in ('partial_update', 'update'):
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), IsCenterDoctor()]
        return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]

    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']


class ReportViewSet(viewsets.ModelViewSet):
    """
    Lab technicians create and update reports; staff verify them.
    Strictly scoped to the current tenant center.
    """

    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        tenant = self.request.tenant
        user = self.request.user
        qs = Report.objects.filter(
            appointment__center=tenant,
        ).select_related(
            'test_type',
            'test_order',
            'appointment__patient',
            'verified_by',
        )
        # Patients can only see their own reports
        if not hasattr(user, 'staff_profile') and not hasattr(user, 'doctor_profile'):
            qs = qs.filter(appointment__patient=user)
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return ReportCreateSerializer
        return ReportSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsCenterLabTechnician()]
        if self.action == 'partial_update':
            return [permissions.IsAuthenticated(), IsCenterLabTechnician()]
        if self.action == 'verify':
            return [permissions.IsAuthenticated(), IsCenterStaff()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, pk=None):
        report = self.get_object()
        if report.status == Report.Status.VERIFIED:
            return Response(
                {'detail': 'Report is already verified.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        report.status = Report.Status.VERIFIED
        report.verified_by = request.user
        report.save(update_fields=['status', 'verified_by', 'updated_at'])
        logger.info(
            'Report verified',
            extra={'report_id': report.id, 'verified_by': request.user.id},
        )
        return Response(ReportSerializer(report).data)
