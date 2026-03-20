import logging

from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from core.tenants.permissions import (
    IsCenterAdmin,
    IsCenterDoctor,
    IsCenterMedicalTechnologist,
    IsCenterStaff,
    IsCenterStaffOrDoctor,
)

from .models import (
    CenterTestPricing,
    ReferringDoctor,
    Report,
    ReportTemplate,
    TestOrder,
    TestType,
)
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
        tags=["Diagnostics"],
        summary="List all test types",
        description="Returns all available diagnostic test types (global, not center-specific).",
    ),
    retrieve=extend_schema(tags=["Diagnostics"], summary="Get test type detail"),
    create=extend_schema(tags=["Diagnostics"], summary="Create a test type"),
    update=extend_schema(tags=["Diagnostics"], summary="Update a test type"),
    partial_update=extend_schema(
        tags=["Diagnostics"], summary="Partial update a test type"
    ),
    destroy=extend_schema(tags=["Diagnostics"], summary="Delete a test type"),
)
class TestTypeViewSet(viewsets.ModelViewSet):
    serializer_class = TestTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return TestType.objects.all()


@extend_schema_view(
    list=extend_schema(
        tags=["Diagnostics"],
        summary="List center test pricing",
        description=(
            "Returns test types with center-specific pricing. "
            "Only shows tests available at the current center."
        ),
    ),
    retrieve=extend_schema(
        tags=["Diagnostics"], summary="Get center test pricing detail"
    ),
    create=extend_schema(tags=["Diagnostics"], summary="Set center test pricing"),
    update=extend_schema(tags=["Diagnostics"], summary="Update center test pricing"),
    partial_update=extend_schema(
        tags=["Diagnostics"], summary="Partial update pricing"
    ),
    destroy=extend_schema(tags=["Diagnostics"], summary="Remove test from center"),
)
class CenterTestPricingViewSet(viewsets.ModelViewSet):
    serializer_class = CenterTestPricingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        tenant = self.request.tenant
        return CenterTestPricing.objects.filter(center=tenant).select_related(
            "test_type"
        )

    def perform_create(self, serializer):
        serializer.save(center=self.request.tenant)


# ─── Report Templates ─────────────────────────────────────────────


@extend_schema_view(
    list=extend_schema(
        tags=["Report Templates"],
        summary="List report templates",
        description="Returns all report templates. Optionally filter by ?test_type=ID.",
    ),
    retrieve=extend_schema(
        tags=["Report Templates"], summary="Get report template detail"
    ),
    create=extend_schema(
        tags=["Report Templates"],
        summary="Create report template",
        description="Create a report template defining expected result fields for a test type.",
    ),
    update=extend_schema(tags=["Report Templates"], summary="Update report template"),
    partial_update=extend_schema(
        tags=["Report Templates"], summary="Partial update template"
    ),
    destroy=extend_schema(tags=["Report Templates"], summary="Delete report template"),
)
class ReportTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = ReportTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCenterMedicalTechnologist]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        qs = ReportTemplate.objects.select_related("test_type", "center")
        if tenant:
            qs = qs.filter(center=tenant)
        test_type = self.request.query_params.get("test_type")
        if test_type:
            qs = qs.filter(test_type_id=test_type)
        return qs

    def perform_create(self, serializer):
        serializer.save(center=self.request.tenant)


# ─── Referring Doctors ─────────────────────────────────────────────


@extend_schema_view(
    list=extend_schema(
        tags=["Referring Doctors"],
        summary="List saved referring doctors",
        description="Returns referring doctors for the current center.",
    ),
    create=extend_schema(
        tags=["Referring Doctors"],
        summary="Add a referring doctor",
    ),
    partial_update=extend_schema(
        tags=["Referring Doctors"],
        summary="Update referring doctor",
    ),
    destroy=extend_schema(
        tags=["Referring Doctors"],
        summary="Delete referring doctor",
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
        tags=["Test Orders"],
        summary="List test orders",
        description=(
            "Returns test orders for the current center. "
            "Filterable by status via `?status=PENDING`. "
            "Doctors see only their prescribed tests; staff see all."
        ),
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter by test order status",
                required=False,
                type=str,
                enum=["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"],
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=["Test Orders"],
        summary="Get test order detail",
    ),
    create=extend_schema(
        tags=["Test Orders"],
        summary="Prescribe a test (doctor only)",
        description=(
            "Doctor creates a test order for a patient's appointment. "
            "The test type must be available at the current center "
            "(must have a `CenterTestPricing` entry with `is_available=True`). "
            "The center and ordering doctor are set automatically."
        ),
        request=TestOrderCreateSerializer,
        responses={201: TestOrderSerializer},
        examples=[
            OpenApiExample(
                "Order a CBC test (urgent)",
                value={
                    "appointment": 1,
                    "test_type": 3,
                    "priority": "URGENT",
                    "clinical_notes": "Patient reports persistent fatigue and dizziness for 2 weeks.",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Order a routine lipid panel",
                value={
                    "appointment": 1,
                    "test_type": 5,
                    "priority": "NORMAL",
                    "clinical_notes": "Annual health check.",
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=["Test Orders"],
        summary="Update test order status",
        description=(
            "Medical technologists update the status of a test order "
            "(e.g., move from `PENDING` to `IN_PROGRESS`)."
        ),
        request=TestOrderStatusUpdateSerializer,
        responses={200: TestOrderSerializer},
        examples=[
            OpenApiExample(
                "Mark as in progress",
                value={"status": "IN_PROGRESS"},
                request_only=True,
            ),
        ],
    ),
    destroy=extend_schema(
        tags=["Test Orders"],
        summary="Cancel a test order (doctor only)",
    ),
)
class TestOrderViewSet(viewsets.ModelViewSet):
    """
    Doctors create test orders; medical technologists and staff manage them.
    Strictly scoped to the current tenant center.
    """

    def get_queryset(self):
        tenant = self.request.tenant
        user = self.request.user
        qs = TestOrder.objects.filter(center=tenant).select_related(
            "test_type",
            "patient",
            "created_by",
        )
        if hasattr(user, "doctor_profile"):
            # Doctors see only orders they referred
            qs = qs.filter(referring_doctor_name__iexact=user.get_full_name())
        elif not hasattr(user, "staff_profile"):
            qs = qs.filter(patient=user)

        params = self.request.query_params
        if status_filter := params.get("status"):
            qs = qs.filter(status=status_filter)
        if patient_id := params.get("patient"):
            qs = qs.filter(patient_id=patient_id)
        if test_type_id := params.get("test_type"):
            qs = qs.filter(test_type_id=test_type_id)

        ordering = params.get("ordering", "-created_at")
        allowed = {
            "created_at",
            "-created_at",
            "priority",
            "-priority",
            "status",
            "-status",
        }
        if ordering in allowed:
            qs = qs.order_by(ordering)

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return TestOrderCreateSerializer
        if self.action in (
            "partial_update",
            "update",
        ) and not IsCenterDoctor().has_permission(self.request, self):
            return TestOrderStatusUpdateSerializer
        return TestOrderSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsCenterDoctor()]
        if self.action in ("partial_update", "update"):
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        if self.action == "destroy":
            return [permissions.IsAuthenticated(), IsCenterDoctor()]
        return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]


# ─── Reports ──────────────────────────────────────────────────────


@extend_schema_view(
    list=extend_schema(
        tags=["Reports"],
        summary="List reports",
        description=(
            "Returns reports for the current center. "
            "Staff/doctors see all reports; patients see only their own."
        ),
    ),
    retrieve=extend_schema(
        tags=["Reports"],
        summary="Get report detail",
        description="Returns a single report with result data, file attachment, and verification status.",
    ),
    create=extend_schema(
        tags=["Reports"],
        summary="Create a report (medical technologist only)",
        description=(
            "Medical technologist creates a report by selecting a test type and patient. "
            "A test order is auto-created in the background with COMPLETED status. "
            "If a report template exists for the test type, result fields are auto-populated."
        ),
        request=ReportCreateSerializer,
        responses={201: ReportSerializer},
        examples=[
            OpenApiExample(
                "Create CBC report with structured results",
                value={
                    "test_type": 3,
                    "patient": 1,
                    "referring_doctor_name": "Dr. Aminul Islam",
                    "result_text": "",
                    "result_data": {
                        "Hemoglobin": {
                            "value": "14.5",
                            "unit": "g/dL",
                            "ref_range": "13.5-17.5",
                            "finding": "Normal",
                        },
                    },
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=["Reports"],
        summary="Update a report (medical technologist only)",
        description="Update report result text, data, or upload file attachment.",
    ),
)
class ReportViewSet(viewsets.ModelViewSet):
    """
    Medical technologists create and update reports; staff verify them.
    Strictly scoped to the current tenant center.
    """

    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "test_order__patient__first_name",
        "test_order__patient__last_name",
        "test_type__name",
        "test_order__referring_doctor_name",
    ]
    ordering_fields = ["created_at", "updated_at", "test_type__name", "status"]
    ordering = ["-updated_at", "-created_at"]

    def get_queryset(self):
        tenant = self.request.tenant
        user = self.request.user
        qs = Report.objects.filter(
            test_order__center=tenant,
            is_deleted=False,
        ).select_related(
            "test_type",
            "test_order__patient",
            "test_order__center",
            "test_order__created_by",
            "verified_by",
        )
        if hasattr(user, "doctor_profile"):
            # Doctors see only reports they referred
            qs = qs.filter(
                test_order__referring_doctor_name__iexact=user.get_full_name(),
            )
        elif not hasattr(user, "staff_profile"):
            qs = qs.filter(test_order__patient=user)

        # Manual query param filters
        params = self.request.query_params
        if patient_id := params.get("patient"):
            qs = qs.filter(test_order__patient_id=patient_id)
        if test_type_id := params.get("test_type"):
            qs = qs.filter(test_type_id=test_type_id)
        if doctor := params.get("referring_doctor"):
            qs = qs.filter(test_order__referring_doctor_name__icontains=doctor)
        if status_val := params.get("status"):
            qs = qs.filter(status=status_val)

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return ReportCreateSerializer
        if self.action == "print_data":
            return ReportPrintSerializer
        return ReportSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsCenterMedicalTechnologist()]
        if self.action in ("partial_update", "update"):
            return [permissions.IsAuthenticated(), IsCenterMedicalTechnologist()]
        if self.action == "destroy":
            return [permissions.IsAuthenticated(), IsCenterMedicalTechnologist()]
        if self.action == "verify":
            return [permissions.IsAuthenticated(), IsCenterAdmin()]
        if self.action == "mark_delivered":
            return [permissions.IsAuthenticated(), IsCenterStaff()]
        # print_data: any authenticated user (patients filtered by get_queryset)
        return [permissions.IsAuthenticated()]

    def perform_destroy(self, instance):
        from django.utils import timezone

        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def create(self, request, *args, **kwargs):
        # ── Report limit enforcement ──
        tenant = request.tenant
        if tenant:
            from apps.subscriptions.models import Subscription

            try:
                sub = (
                    Subscription.objects.select_related("plan")
                    .filter(
                        center=tenant,
                    )
                    .latest("started_at")
                )
                max_reports = sub.plan.max_reports
                if max_reports != -1:
                    now = timezone.now()
                    current_count = Report.objects.filter(
                        test_order__center=tenant,
                        created_at__year=now.year,
                        created_at__month=now.month,
                        is_deleted=False,
                    ).count()
                    if current_count >= max_reports:
                        return Response(
                            {
                                "detail": (
                                    f"Monthly report limit ({max_reports}) reached. "
                                    f"Upgrade your plan for more reports."
                                ),
                                "current_count": current_count,
                                "max_reports": max_reports,
                            },
                            status=status.HTTP_403_FORBIDDEN,
                        )
            except Subscription.DoesNotExist:
                pass

        serializer = ReportCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        return Response(
            ReportSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["Reports"],
        summary="Verify a report",
        description=(
            "Staff verifies a draft report, changing its status to `VERIFIED`. "
            "The verifying user is recorded. A report can only be verified once."
        ),
        request=None,
        responses={200: ReportSerializer},
    )
    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request, pk=None):
        report = self.get_object()
        if report.status == Report.Status.VERIFIED:
            return Response(
                {"detail": "Report is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        report.status = Report.Status.VERIFIED
        report.verified_by = request.user
        report.verified_at = timezone.now()
        report.save(
            update_fields=["status", "verified_by", "verified_at", "updated_at"]
        )
        logger.info(
            "Report verified",
            extra={"report_id": report.id, "verified_by": request.user.id},
        )

        # Send email notification to patient (skip if no email)
        try:
            patient = report.test_order.patient
            email = getattr(patient, "email", None)
            if email:
                from apps.diagnostics.services.notifications import (
                    send_report_ready_email,
                )

                send_report_ready_email(report, email)
        except Exception:
            logger.exception("Failed to send report notification email")

        return Response(ReportSerializer(report).data)

    @extend_schema(
        tags=["Reports"],
        summary="Get report print data",
        description=(
            "Returns comprehensive report data for printing, including "
            "center details, patient info, referring doctor, medical technologist, "
            "and structured test results."
        ),
        responses={200: ReportPrintSerializer},
    )
    @action(detail=True, methods=["get"], url_path="print-data")
    def print_data(self, request, pk=None):
        report = self.get_object()
        serializer = ReportPrintSerializer(report, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        tags=["Reports"],
        summary="Mark report as delivered",
        description=(
            "Transitions a VERIFIED report to DELIVERED status. "
            "Called automatically after the report is printed."
        ),
        request=None,
        responses={200: ReportSerializer},
    )
    @action(detail=True, methods=["post"], url_path="mark-delivered")
    def mark_delivered(self, request, pk=None):
        report = self.get_object()
        if report.status == Report.Status.DELIVERED:
            return Response(
                {"detail": "Report is already delivered."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if report.status != Report.Status.VERIFIED:
            return Response(
                {"detail": "Only verified reports can be marked as delivered."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        report.status = Report.Status.DELIVERED
        report.save(update_fields=["status", "updated_at"])
        logger.info(
            "Report marked as delivered",
            extra={"report_id": report.id, "delivered_by": request.user.id},
        )
        return Response(ReportSerializer(report).data)

    @extend_schema(
        tags=["Reports"],
        summary="Get result history for delta check",
        description=(
            "Returns the last 5 reports for a given patient + test type "
            "combination. Used for delta check during report entry."
        ),
        parameters=[
            OpenApiParameter(
                name="patient_id",
                description="Patient user ID",
                required=True,
                type=int,
            ),
            OpenApiParameter(
                name="test_type_id",
                description="Test type ID",
                required=True,
                type=int,
            ),
        ],
    )
    @action(detail=False, methods=["get"], url_path="result-history")
    def result_history(self, request):
        patient_id = request.query_params.get("patient_id")
        test_type_id = request.query_params.get("test_type_id")
        if not patient_id or not test_type_id:
            return Response(
                {"detail": "patient_id and test_type_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant = request.tenant
        previous_reports = (
            Report.objects.filter(
                test_order__center=tenant,
                test_order__patient_id=patient_id,
                test_type_id=test_type_id,
                is_deleted=False,
            )
            .exclude(result_data={})
            .order_by("-created_at")[:5]
        )

        history = []
        for report in previous_reports:
            history.append(
                {
                    "id": report.id,
                    "date": report.created_at.isoformat(),
                    "result_data": report.result_data,
                }
            )

        return Response(history)


# ─── Public Report Access (no auth) ──────────────────────────
class PublicReportView(APIView):
    """Token-based public access to a report. No authentication required."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Public"],
        summary="View report via access token",
        description=(
            "Returns report data for public viewing via a unique access token. "
            "No authentication required. Used for digital report delivery."
        ),
    )
    def get(self, request, access_token):
        from django.db.models import F

        try:
            report = Report.objects.select_related(
                "test_type",
                "test_order__patient",
                "test_order__center",
                "created_by",
            ).get(access_token=access_token, is_deleted=False)
        except Report.DoesNotExist:
            return Response(
                {"detail": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Increment access count
        Report.objects.filter(id=report.id).update(access_count=F("access_count") + 1)

        serializer = ReportPrintSerializer(report, context={"request": request})
        return Response(serializer.data)


# ─── Analytics ────────────────────────────────────────────────
class AnalyticsViewSet(viewsets.ViewSet):
    """Business analytics endpoints for center dashboards."""

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    @extend_schema(
        tags=["Analytics"],
        summary="Revenue breakdown by test type",
        parameters=[
            OpenApiParameter(name="start_date", type=str, required=False),
            OpenApiParameter(name="end_date", type=str, required=False),
        ],
    )
    @action(detail=False, methods=["get"], url_path="revenue-by-test")
    def revenue_by_test(self, request):
        from apps.diagnostics.services.analytics import revenue_by_test_type

        tenant = request.tenant
        start = request.query_params.get("start_date")
        end = request.query_params.get("end_date")
        data = revenue_by_test_type(tenant, start, end)
        return Response(data)

    @extend_schema(
        tags=["Analytics"],
        summary="Revenue trends over time",
        parameters=[
            OpenApiParameter(
                name="period",
                type=str,
                required=False,
                enum=["daily", "weekly", "monthly"],
            ),
            OpenApiParameter(name="days", type=int, required=False),
        ],
    )
    @action(detail=False, methods=["get"], url_path="revenue-trends")
    def revenue_trends(self, request):
        from apps.diagnostics.services.analytics import revenue_trends as rt

        tenant = request.tenant
        period = request.query_params.get("period", "daily")
        days = int(request.query_params.get("days", 30))
        data = rt(tenant, period, days)
        return Response(data)

    @extend_schema(
        tags=["Analytics"],
        summary="Revenue by referring doctor",
        parameters=[
            OpenApiParameter(name="start_date", type=str, required=False),
            OpenApiParameter(name="end_date", type=str, required=False),
        ],
    )
    @action(detail=False, methods=["get"], url_path="revenue-by-doctor")
    def revenue_by_doctor(self, request):
        from apps.diagnostics.services.analytics import (
            revenue_by_doctor as rbd,
        )

        tenant = request.tenant
        start = request.query_params.get("start_date")
        end = request.query_params.get("end_date")
        data = rbd(tenant, start, end)
        return Response(data)

    @extend_schema(
        tags=["Analytics"],
        summary="Patient metrics (new vs returning)",
        parameters=[
            OpenApiParameter(name="days", type=int, required=False),
        ],
    )
    @action(detail=False, methods=["get"], url_path="patient-metrics")
    def patient_metrics(self, request):
        from apps.diagnostics.services.analytics import (
            patient_metrics as pm,
        )

        tenant = request.tenant
        days = int(request.query_params.get("days", 30))
        data = pm(tenant, days)
        return Response(data)

    @extend_schema(
        tags=["Analytics"],
        summary="Turnaround time statistics",
        parameters=[
            OpenApiParameter(name="days", type=int, required=False),
        ],
    )
    @action(detail=False, methods=["get"], url_path="tat-stats")
    def tat_stats(self, request):
        from apps.diagnostics.services.analytics import (
            turnaround_time_stats,
        )

        tenant = request.tenant
        days = int(request.query_params.get("days", 30))
        data = turnaround_time_stats(tenant, days)
        return Response(data)
