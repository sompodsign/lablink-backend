import logging

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.appointments.models import Appointment
from apps.diagnostics.models import Report, TestOrder
from core.tenants.permissions import IsSuperAdmin

from .models import DiagnosticCenter, Doctor, Staff
from .superadmin_serializers import (
    SuperadminCenterDetailSerializer,
    SuperadminCenterSerializer,
    SuperadminDoctorSerializer,
    SuperadminPatientSerializer,
    SuperadminStaffSerializer,
    SuperadminStatsSerializer,
    SuperadminUserSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ── Shared permission base ───────────────────────────────────────


class SuperadminBaseView(APIView):
    """Base view that enforces superadmin access."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]


# ── Dashboard Stats ──────────────────────────────────────────────


@extend_schema(
    tags=["Superadmin"],
    summary="Platform overview stats",
    responses=SuperadminStatsSerializer,
)
class SuperadminDashboardView(SuperadminBaseView):
    """Aggregate stats across all centers."""

    def get(self, request):
        from core.users.models import PatientProfile

        data = {
            "total_centers": DiagnosticCenter.objects.count(),
            "active_centers": DiagnosticCenter.objects.filter(
                is_active=True,
            ).count(),
            "inactive_centers": DiagnosticCenter.objects.filter(
                is_active=False,
            ).count(),
            "total_users": User.objects.count(),
            "total_patients": PatientProfile.objects.count(),
            "total_staff": Staff.objects.count(),
            "total_doctors": Doctor.objects.count(),
            "total_appointments": Appointment.objects.count(),
            "total_test_orders": TestOrder.objects.count(),
            "total_reports": Report.objects.count(),
        }
        return Response(SuperadminStatsSerializer(data).data)


# ── Centers ──────────────────────────────────────────────────────


@extend_schema(
    tags=["Superadmin"],
    summary="List all diagnostic centers",
    responses=SuperadminCenterSerializer(many=True),
)
class SuperadminCenterListView(SuperadminBaseView):
    """List all centers with staff/doctor/patient counts."""

    def get(self, request):
        centers = DiagnosticCenter.objects.annotate(
            staff_count=Count("staff", distinct=True),
            doctor_count=Count(
                "users",
                filter=Q(users__doctor_profile__isnull=False),
                distinct=True,
            ),
            patient_count=Count("registered_patients", distinct=True),
        ).order_by("name")

        serializer = SuperadminCenterSerializer(
            centers,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


@extend_schema(
    tags=["Superadmin"],
    summary="Get or update a center",
)
class SuperadminCenterDetailView(SuperadminBaseView):
    """Retrieve or update a specific center."""

    def get(self, request, center_id):
        try:
            center = DiagnosticCenter.objects.annotate(
                staff_count=Count("staff", distinct=True),
                doctor_count=Count(
                    "users",
                    filter=Q(users__doctor_profile__isnull=False),
                    distinct=True,
                ),
                patient_count=Count("registered_patients", distinct=True),
            ).get(pk=center_id)
        except DiagnosticCenter.DoesNotExist:
            return Response(
                {"detail": "Center not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SuperadminCenterDetailSerializer(
            center,
            context={"request": request},
        )
        return Response(serializer.data)

    def patch(self, request, center_id):
        try:
            center = DiagnosticCenter.objects.get(pk=center_id)
        except DiagnosticCenter.DoesNotExist:
            return Response(
                {"detail": "Center not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SuperadminCenterDetailSerializer(
            center,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(
            "Superadmin %s updated center %s",
            request.user.username,
            center.name,
        )
        return Response(serializer.data)


@extend_schema(
    tags=["Superadmin"],
    summary="Toggle center active/inactive",
)
class SuperadminCenterToggleView(SuperadminBaseView):
    """Activate or deactivate a diagnostic center."""

    def post(self, request, center_id):
        try:
            center = DiagnosticCenter.objects.get(pk=center_id)
        except DiagnosticCenter.DoesNotExist:
            return Response(
                {"detail": "Center not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        center.is_active = not center.is_active
        center.save(update_fields=["is_active"])

        action = "activated" if center.is_active else "deactivated"
        logger.info(
            "Superadmin %s %s center %s",
            request.user.username,
            action,
            center.name,
        )
        return Response(
            {
                "detail": f'Center "{center.name}" {action}.',
                "is_active": center.is_active,
            }
        )


# ── Users ────────────────────────────────────────────────────────


@extend_schema(
    tags=["Superadmin"],
    summary="List all users across centers",
    responses=SuperadminUserSerializer(many=True),
)
class SuperadminUserListView(SuperadminBaseView):
    """List all users with center/role info."""

    def get(self, request):
        users = (
            User.objects.select_related(
                "staff_profile__center",
                "staff_profile__role",
                "center",
            )
            .prefetch_related("patient_profile")
            .order_by("-date_joined")
        )

        # Optional filters
        center_id = request.query_params.get("center")
        user_type = request.query_params.get("type")
        search = request.query_params.get("search", "").strip()

        if center_id:
            users = users.filter(center_id=center_id)

        if user_type == "staff":
            users = users.filter(staff_profile__isnull=False)
        elif user_type == "doctor":
            users = users.filter(doctor_profile__isnull=False)
        elif user_type == "patient":
            users = users.filter(patient_profile__isnull=False)
        elif user_type == "superadmin":
            users = users.filter(is_superuser=True)

        if search:
            users = users.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(username__icontains=search),
            )

        serializer = SuperadminUserSerializer(users[:100], many=True)
        return Response(serializer.data)


@extend_schema(
    tags=["Superadmin"],
    summary="Get, update, or delete a user",
)
class SuperadminUserDetailView(SuperadminBaseView):
    """View, update, or delete any user."""

    def get(self, request, user_id):
        try:
            user = (
                User.objects.select_related(
                    "staff_profile__center",
                    "staff_profile__role",
                    "center",
                )
                .prefetch_related(
                    "patient_profile",
                )
                .get(pk=user_id)
            )
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(SuperadminUserSerializer(user).data)

    def patch(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SuperadminUserSerializer(
            user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(
            "Superadmin %s updated user %s",
            request.user.username,
            user.username,
        )
        return Response(serializer.data)

    def delete(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_superuser:
            return Response(
                {"detail": "Cannot delete a superadmin user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = user.username
        user.delete()
        logger.info(
            "Superadmin %s deleted user %s",
            request.user.username,
            username,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Patients ─────────────────────────────────────────────────────


@extend_schema(
    tags=["Superadmin"],
    summary="List all patients across centers",
    responses=SuperadminPatientSerializer(many=True),
)
class SuperadminPatientListView(SuperadminBaseView):
    """All patient profiles across all centers."""

    def get(self, request):
        from core.users.models import PatientProfile

        patients = PatientProfile.objects.select_related(
            "user", "registered_at_center"
        ).order_by("-created_at")

        center_id = request.query_params.get("center")
        if center_id:
            patients = patients.filter(
                registered_at_center_id=center_id,
            )

        serializer = SuperadminPatientSerializer(patients[:100], many=True)
        return Response(serializer.data)


# ── Staff ────────────────────────────────────────────────────────


@extend_schema(
    tags=["Superadmin"],
    summary="List all staff across centers",
    responses=SuperadminStaffSerializer(many=True),
)
class SuperadminStaffListView(SuperadminBaseView):
    """All staff members across all centers."""

    def get(self, request):
        staff = Staff.objects.select_related("user", "center", "role").order_by(
            "center__name", "user__first_name"
        )

        center_id = request.query_params.get("center")
        if center_id:
            staff = staff.filter(center_id=center_id)

        serializer = SuperadminStaffSerializer(staff, many=True)
        return Response(serializer.data)


# ── Doctors ──────────────────────────────────────────────────────


@extend_schema(
    tags=["Superadmin"],
    summary="List all doctors across centers",
    responses=SuperadminDoctorSerializer(many=True),
)
class SuperadminDoctorListView(SuperadminBaseView):
    """All doctors across all centers."""

    def get(self, request):
        doctors = Doctor.objects.select_related("user", "user__center").order_by(
            "user__first_name"
        )

        center_id = request.query_params.get("center")
        if center_id:
            doctors = doctors.filter(user__center_id=center_id)

        serializer = SuperadminDoctorSerializer(doctors, many=True)
        return Response(serializer.data)
