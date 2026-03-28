import logging

from django.utils import timezone as dj_timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.tenants.permissions import IsCenterStaffOrDoctor

from .models import FollowUp
from .serializers import (
    CancelSerializer,
    CompleteSerializer,
    FollowUpCreateSerializer,
    FollowUpSerializer,
    FollowUpUpdateSerializer,
)

logger = logging.getLogger(__name__)


def _has_manage_followups(request) -> bool:
    """Check if the staff user has manage_followups permission."""
    return hasattr(
        request.user, "staff_profile"
    ) and request.user.staff_profile.has_perm("manage_followups")


def _is_doctor(request) -> bool:
    return hasattr(request.user, "doctor_profile")


@extend_schema_view(
    list=extend_schema(
        tags=["Follow-Ups"],
        summary="List follow-ups",
        description=(
            "Returns follow-ups for the current center.\n\n"
            "- **Doctors** without `manage_followups` see only their own follow-ups.\n"
            "- **Staff / doctors with `manage_followups`** see all center follow-ups."
        ),
        parameters=[
            OpenApiParameter(
                "status", str, description="Filter: PENDING, COMPLETED, CANCELLED"
            ),
            OpenApiParameter("doctor", int, description="Filter by doctor ID"),
            OpenApiParameter("patient", int, description="Filter by patient (user) ID"),
            OpenApiParameter(
                "appointment", int, description="Filter by appointment ID"
            ),
            OpenApiParameter("date_from", str, description="scheduled_date >="),
            OpenApiParameter("date_to", str, description="scheduled_date <="),
            OpenApiParameter(
                "overdue",
                bool,
                description="If true, return PENDING with scheduled_date < today",
            ),
        ],
    ),
    retrieve=extend_schema(tags=["Follow-Ups"], summary="Get follow-up detail"),
    create=extend_schema(
        tags=["Follow-Ups"],
        summary="Create a follow-up",
        description="Doctor or staff schedules a follow-up for a patient. Center is injected from tenant context.",
        examples=[
            OpenApiExample(
                "Create follow-up",
                value={
                    "patient": 5,
                    "doctor": 2,
                    "scheduled_date": "2026-04-10",
                    "reason": "CBC recheck after iron supplement course",
                    "notes": "Fasting required",
                },
                request_only=True,
            )
        ],
    ),
    partial_update=extend_schema(
        tags=["Follow-Ups"],
        summary="Update a follow-up",
        description="Only PENDING follow-ups can be edited. Returns 400 for COMPLETED or CANCELLED.",
    ),
    destroy=extend_schema(
        tags=["Follow-Ups"],
        summary="Delete a follow-up",
        description="Only PENDING follow-ups can be deleted. Requires `manage_followups` permission.",
    ),
)
class FollowUpViewSet(viewsets.ModelViewSet):
    permission_classes = [IsCenterStaffOrDoctor]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        tenant = self.request.tenant
        qs = FollowUp.objects.filter(center=tenant).select_related(
            "patient", "doctor", "appointment", "created_by"
        )

        # Doctors without manage_followups can only see their own
        if _is_doctor(self.request) and not _has_manage_followups(self.request):
            try:
                qs = qs.filter(doctor=self.request.user.doctor_profile)
            except Exception:
                qs = qs.none()

        # Apply filters
        params = self.request.query_params
        if status_filter := params.get("status"):
            qs = qs.filter(status=status_filter.upper())
        if doctor_id := params.get("doctor"):
            qs = qs.filter(doctor_id=doctor_id)
        if patient_id := params.get("patient"):
            qs = qs.filter(patient_id=patient_id)
        if appointment_id := params.get("appointment"):
            qs = qs.filter(appointment_id=appointment_id)
        if date_from := params.get("date_from"):
            qs = qs.filter(scheduled_date__gte=date_from)
        if date_to := params.get("date_to"):
            qs = qs.filter(scheduled_date__lte=date_to)
        if params.get("overdue", "").lower() in ("true", "1", "yes"):
            from datetime import date

            qs = qs.filter(
                status=FollowUp.STATUS_PENDING,
                scheduled_date__lt=date.today(),
            )

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return FollowUpCreateSerializer
        if self.action == "partial_update":
            return FollowUpUpdateSerializer
        return FollowUpSerializer

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.is_resolved:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                "Cannot edit a resolved follow-up (COMPLETED or CANCELLED)."
            )
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        if not _has_manage_followups(request):
            return Response(
                {"detail": "You do not have permission to delete follow-ups."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        if instance.is_resolved:
            return Response(
                {"detail": "Cannot delete a resolved follow-up."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=["Follow-Ups"],
        summary="Complete a follow-up",
        description="Marks the follow-up as COMPLETED. Returns 400 if already resolved.",
        request=CompleteSerializer,
        responses={200: FollowUpSerializer},
    )
    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        instance = self.get_object()
        if instance.is_resolved:
            return Response(
                {"detail": f"Follow-up is already {instance.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get("notes"):
            instance.notes = serializer.validated_data["notes"]
        instance.status = FollowUp.STATUS_COMPLETED
        instance.completed_at = dj_timezone.now()
        instance.updated_by = request.user
        instance.save()

        logger.info("FollowUp %s marked COMPLETED by %s", instance.pk, request.user)
        return Response(FollowUpSerializer(instance).data)

    @extend_schema(
        tags=["Follow-Ups"],
        summary="Cancel a follow-up",
        description="Marks the follow-up as CANCELLED. `cancel_reason` is required. Returns 400 if already resolved.",
        request=CancelSerializer,
        responses={200: FollowUpSerializer},
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        instance = self.get_object()
        if instance.is_resolved:
            return Response(
                {"detail": f"Follow-up is already {instance.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        instance.status = FollowUp.STATUS_CANCELLED
        instance.cancel_reason = serializer.validated_data["cancel_reason"]
        if serializer.validated_data.get("notes"):
            instance.notes = serializer.validated_data["notes"]
        instance.updated_by = request.user
        instance.save()

        logger.info("FollowUp %s CANCELLED by %s", instance.pk, request.user)
        return Response(FollowUpSerializer(instance).data)
