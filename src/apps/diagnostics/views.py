import logging

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.tenants.permissions import (
    IsCenterDoctor,
    IsCenterLabTechnician,
    IsCenterStaff,
    IsCenterStaffOrDoctor,
)

from .models import CenterTestPricing, ReferringDoctor, Report, ReportTemplate, TestOrder, TestType
from .serializers import (
    CenterTestPricingSerializer,
    ReferringDoctorSerializer,
    ReportCreateSerializer,
    ReportPrintSerializer,
    ReportSerializer,
    ReportTemplateSerializer,
    TestOrderCreateSerializer,
    TestOrderSerializer,
    TestOrderStatusUpdateSerializer,
    TestTypeSerializer,
)

logger = logging.getLogger(__name__)


# ─── Test Types & Pricing ──────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=['Diagnostics'],
        summary='List all test types',
        description='Returns all available diagnostic test types (global, not center-specific).',
    ),
    retrieve=extend_schema(tags=['Diagnostics'], summary='Get test type detail'),
    create=extend_schema(tags=['Diagnostics'], summary='Create a test type'),
    update=extend_schema(tags=['Diagnostics'], summary='Update a test type'),
    partial_update=extend_schema(tags=['Diagnostics'], summary='Partial update a test type'),
    destroy=extend_schema(tags=['Diagnostics'], summary='Delete a test type'),
)
class TestTypeViewSet(viewsets.ModelViewSet):
    serializer_class = TestTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return TestType.objects.all()


@extend_schema_view(
    list=extend_schema(
        tags=['Diagnostics'],
        summary='List center test pricing',
        description=(
            'Returns test types with center-specific pricing. '
            'Only shows tests available at the current center.'
        ),
    ),
    retrieve=extend_schema(tags=['Diagnostics'], summary='Get center test pricing detail'),
    create=extend_schema(tags=['Diagnostics'], summary='Set center test pricing'),
    update=extend_schema(tags=['Diagnostics'], summary='Update center test pricing'),
    partial_update=extend_schema(tags=['Diagnostics'], summary='Partial update pricing'),
    destroy=extend_schema(tags=['Diagnostics'], summary='Remove test from center'),
)
class CenterTestPricingViewSet(viewsets.ModelViewSet):
    serializer_class = CenterTestPricingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        tenant = self.request.tenant
        return CenterTestPricing.objects.filter(center=tenant).select_related('test_type')


# ─── Report Templates ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=['Report Templates'],
        summary='List report templates',
        description='Returns all report templates. Optionally filter by ?test_type=ID.',
    ),
    retrieve=extend_schema(tags=['Report Templates'], summary='Get report template detail'),
    create=extend_schema(
        tags=['Report Templates'],
        summary='Create report template',
        description='Create a report template defining expected result fields for a test type.',
    ),
    update=extend_schema(tags=['Report Templates'], summary='Update report template'),
    partial_update=extend_schema(tags=['Report Templates'], summary='Partial update template'),
    destroy=extend_schema(tags=['Report Templates'], summary='Delete report template'),
)
class ReportTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = ReportTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCenterStaffOrDoctor]

    def get_queryset(self):
        qs = ReportTemplate.objects.select_related('test_type').all()
        test_type = self.request.query_params.get('test_type')
        if test_type:
            qs = qs.filter(test_type_id=test_type)
        return qs


# ─── Referring Doctors ─────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=['Referring Doctors'],
        summary='List saved referring doctors',
        description='Returns referring doctors for the current center.',
    ),
    create=extend_schema(
        tags=['Referring Doctors'],
        summary='Add a referring doctor',
    ),
    partial_update=extend_schema(
        tags=['Referring Doctors'],
        summary='Update referring doctor',
    ),
    destroy=extend_schema(
        tags=['Referring Doctors'],
        summary='Delete referring doctor',
    ),
)
class ReferringDoctorViewSet(viewsets.ModelViewSet):
    serializer_class = ReferringDoctorSerializer
    permission_classes = [permissions.IsAuthenticated, IsCenterStaffOrDoctor]

    def get_queryset(self):
        tenant = self.request.tenant
        return ReferringDoctor.objects.filter(center=tenant, is_active=True)


# ─── Test Orders ───────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=['Test Orders'],
        summary='List test orders',
        description=(
            'Returns test orders for the current center. '
            'Filterable by status via `?status=PENDING`. '
            'Doctors see only their prescribed tests; staff see all.'
        ),
        parameters=[
            OpenApiParameter(
                name='status',
                description='Filter by test order status',
                required=False,
                type=str,
                enum=['PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'],
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=['Test Orders'],
        summary='Get test order detail',
    ),
    create=extend_schema(
        tags=['Test Orders'],
        summary='Prescribe a test (doctor only)',
        description=(
            'Doctor creates a test order for a patient\'s appointment. '
            'The test type must be available at the current center '
            '(must have a `CenterTestPricing` entry with `is_available=True`). '
            'The center and ordering doctor are set automatically.'
        ),
        request=TestOrderCreateSerializer,
        responses={201: TestOrderSerializer},
        examples=[
            OpenApiExample(
                'Order a CBC test (urgent)',
                value={
                    'appointment': 1,
                    'test_type': 3,
                    'priority': 'URGENT',
                    'clinical_notes': 'Patient reports persistent fatigue and dizziness for 2 weeks.',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Order a routine lipid panel',
                value={
                    'appointment': 1,
                    'test_type': 5,
                    'priority': 'NORMAL',
                    'clinical_notes': 'Annual health check.',
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=['Test Orders'],
        summary='Update test order status',
        description=(
            'Lab technicians update the status of a test order '
            '(e.g., move from `PENDING` to `IN_PROGRESS`).'
        ),
        request=TestOrderStatusUpdateSerializer,
        responses={200: TestOrderSerializer},
        examples=[
            OpenApiExample(
                'Mark as in progress',
                value={'status': 'IN_PROGRESS'},
                request_only=True,
            ),
        ],
    ),
    destroy=extend_schema(
        tags=['Test Orders'],
        summary='Cancel a test order (doctor only)',
    ),
)
class TestOrderViewSet(viewsets.ModelViewSet):
    """
    Doctors create test orders; lab technicians and staff manage them.
    Strictly scoped to the current tenant center.
    """

    def get_queryset(self):
        tenant = self.request.tenant
        qs = TestOrder.objects.filter(center=tenant).select_related(
            'test_type',
            'patient',
            'created_by',
        )
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


# ─── Reports ──────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        tags=['Reports'],
        summary='List reports',
        description=(
            'Returns reports for the current center. '
            'Staff/doctors see all reports; patients see only their own.'
        ),
    ),
    retrieve=extend_schema(
        tags=['Reports'],
        summary='Get report detail',
        description='Returns a single report with result data, file attachment, and verification status.',
    ),
    create=extend_schema(
        tags=['Reports'],
        summary='Create a report (lab technician only)',
        description=(
            'Lab technician creates a report by selecting a test type and patient. '
            'A test order is auto-created in the background with COMPLETED status. '
            'If a report template exists for the test type, result fields are auto-populated.'
        ),
        request=ReportCreateSerializer,
        responses={201: ReportSerializer},
        examples=[
            OpenApiExample(
                'Create CBC report with structured results',
                value={
                    'test_type': 3,
                    'patient': 1,
                    'referring_doctor_name': 'Dr. Aminul Islam',
                    'result_text': '',
                    'result_data': {
                        'Hemoglobin': {
                            'value': '14.5',
                            'unit': 'g/dL',
                            'ref_range': '13.5-17.5',
                            'finding': 'Normal',
                        },
                    },
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=['Reports'],
        summary='Update a report (lab technician only)',
        description='Update report result text, data, or upload file attachment.',
    ),
)
class ReportViewSet(viewsets.ModelViewSet):
    """
    Lab technicians create and update reports; staff verify them.
    Strictly scoped to the current tenant center.
    """

    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        tenant = self.request.tenant
        user = self.request.user
        qs = Report.objects.filter(
            test_order__center=tenant,
            is_deleted=False,
        ).select_related(
            'test_type',
            'test_order__patient',
            'test_order__center',
            'test_order__created_by',
            'verified_by',
        )
        if not hasattr(user, 'staff_profile') and not hasattr(user, 'doctor_profile'):
            qs = qs.filter(test_order__patient=user)
        return qs.order_by('-updated_at', '-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return ReportCreateSerializer
        if self.action == 'print_data':
            return ReportPrintSerializer
        return ReportSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsCenterLabTechnician()]
        if self.action in ('partial_update', 'update'):
            return [permissions.IsAuthenticated(), IsCenterLabTechnician()]
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), IsCenterLabTechnician()]
        if self.action == 'verify':
            return [permissions.IsAuthenticated(), IsCenterStaff()]
        if self.action == 'print_data':
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        return [permissions.IsAuthenticated()]

    def perform_destroy(self, instance):
        from django.utils import timezone
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])

    def create(self, request, *args, **kwargs):
        serializer = ReportCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        return Response(
            ReportSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=['Reports'],
        summary='Verify a report',
        description=(
            'Staff verifies a draft report, changing its status to `VERIFIED`. '
            'The verifying user is recorded. A report can only be verified once.'
        ),
        request=None,
        responses={200: ReportSerializer},
    )
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

    @extend_schema(
        tags=['Reports'],
        summary='Get report print data',
        description=(
            'Returns comprehensive report data for printing, including '
            'center details, patient info, referring doctor, lab technician, '
            'and structured test results.'
        ),
        responses={200: ReportPrintSerializer},
    )
    @action(detail=True, methods=['get'], url_path='print-data')
    def print_data(self, request, pk=None):
        report = self.get_object()
        serializer = ReportPrintSerializer(report, context={'request': request})
        return Response(serializer.data)
