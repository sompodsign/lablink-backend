import logging

from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.tenants.permissions import IsCenterAdmin, IsCenterStaff, IsCenterStaffOrDoctor

from .models import Doctor, Staff
from .serializers import (
    DiagnosticCenterSerializer,
    DoctorActivitySerializer,
    DoctorManagementSerializer,
    StaffSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Tenant"],
    summary="Get current center info",
    description=(
        "Returns branding and configuration for the diagnostic center "
        "identified by the request subdomain. **No authentication required.** "
        "Used by the frontend to load logos, colors, and service listings dynamically."
    ),
    responses={
        200: DiagnosticCenterSerializer,
        404: {"description": "No diagnostic center found for this domain"},
    },
)
class CurrentTenantView(APIView):
    permission_classes = []  # Public endpoint

    def get(self, request):
        tenant = getattr(request, "tenant", None)
        if tenant:
            serializer = DiagnosticCenterSerializer(
                tenant, context={"request": request}
            )
            return Response(serializer.data)
        return Response(
            {"error": "No diagnostic center found for this domain"},
            status=status.HTTP_404_NOT_FOUND,
        )


@extend_schema_view(
    list=extend_schema(
        tags=["Doctors"],
        summary="List doctors",
        description="Returns all doctors associated with the current center. Requires staff role.",
    ),
    retrieve=extend_schema(
        tags=["Doctors"],
        summary="Get doctor detail",
        description="Returns a single doctor profile with specialization and bio.",
    ),
)
class DoctorManagementViewSet(viewsets.ReadOnlyModelViewSet):
    """Staff manage doctors associated with their center."""

    serializer_class = DoctorManagementSerializer

    def get_queryset(self):
        tenant = self.request.tenant
        return (
            Doctor.objects.filter(centers=tenant)
            .select_related("user")
            .order_by("user__first_name")
        )

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        return [permissions.IsAuthenticated(), IsCenterStaff()]

    @extend_schema(
        tags=["Doctors"],
        summary="Add doctor to center",
        description=(
            "Admin adds an existing doctor (by ID) to the current center. "
            "This creates the M2M relationship — it does NOT create a new doctor record."
        ),
        request=None,
        responses={200: DoctorManagementSerializer},
    )
    @action(detail=True, methods=["post"], url_path="add-to-center")
    def add_to_center(self, request, pk=None):
        if not IsCenterAdmin().has_permission(request, self):
            return Response(
                {"detail": "Only admins can add doctors to the center."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            doctor = Doctor.objects.get(pk=pk)
        except Doctor.DoesNotExist:
            return Response(
                {"detail": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND
            )

        tenant = request.tenant
        doctor.centers.add(tenant)
        logger.info(
            "Doctor added to center",
            extra={"doctor_id": doctor.id, "center_id": tenant.id},
        )
        return Response(DoctorManagementSerializer(doctor).data)

    @extend_schema(
        tags=["Doctors"],
        summary="Remove doctor from center",
        description=(
            "Admin removes a doctor from the current center. "
            "This only removes the M2M relationship — the doctor record is NOT deleted."
        ),
        request=None,
        responses={204: None},
    )
    @action(detail=True, methods=["post"], url_path="remove-from-center")
    def remove_from_center(self, request, pk=None):
        if not IsCenterAdmin().has_permission(request, self):
            return Response(
                {"detail": "Only admins can remove doctors from the center."},
                status=status.HTTP_403_FORBIDDEN,
            )
        doctor = self.get_object()
        tenant = request.tenant
        doctor.centers.remove(tenant)
        logger.info(
            "Doctor removed from center",
            extra={"doctor_id": doctor.id, "center_id": tenant.id},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=["Doctors"],
        summary="Get doctor activity at this center",
        description=(
            "Returns a summary of the doctor's recent activity at the current center, "
            "including total appointments, total test orders prescribed, and last 10 consultations."
        ),
        responses={200: DoctorActivitySerializer},
        examples=[
            OpenApiExample(
                "Doctor activity response",
                value={
                    "doctor": {
                        "id": 1,
                        "name": "Dr. Rina Akter",
                        "email": "rina@example.com",
                        "specialization": "Cardiology",
                        "designation": "Senior Consultant",
                    },
                    "total_appointments": 42,
                    "total_test_orders": 87,
                    "recent_appointments": [
                        {
                            "id": 101,
                            "patient": "Karim Ahmed",
                            "date": "2026-03-05",
                            "status": "COMPLETED",
                        }
                    ],
                },
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["get"], url_path="activity")
    def activity(self, request, pk=None):
        doctor = self.get_object()
        tenant = request.tenant

        appointments = (
            doctor.appointments.filter(center=tenant)
            .select_related("patient")
            .order_by("-date", "-time")
        )
        test_orders = doctor.user.created_test_orders.filter(center=tenant)

        recent = [
            {
                "id": a.id,
                "patient": a.patient.get_full_name(),
                "date": a.date.isoformat(),
                "status": a.status,
            }
            for a in appointments[:10]
        ]

        data = {
            "doctor": DoctorManagementSerializer(doctor).data,
            "total_appointments": appointments.count(),
            "total_test_orders": test_orders.count(),
            "recent_appointments": recent,
        }
        return Response(data)


@extend_schema_view(
    list=extend_schema(
        tags=["Staff"],
        summary="List staff members",
        description="Returns all staff members at the current center. Admin only.",
    ),
    retrieve=extend_schema(
        tags=["Staff"],
        summary="Get staff detail",
    ),
)
class StaffViewSet(viewsets.ReadOnlyModelViewSet):
    """Staff listing for the current center (admin use)."""

    serializer_class = StaffSerializer
    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def get_queryset(self):
        tenant = self.request.tenant
        return Staff.objects.filter(center=tenant).select_related("user")
