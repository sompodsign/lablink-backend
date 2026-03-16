import logging

from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.tenants.permissions import IsCenterAdmin, IsCenterStaff, IsCenterStaffOrDoctor, IsSuperAdmin

from .models import DiagnosticCenter, Doctor, Permission, Role, Staff
from .serializers import (
    DiagnosticCenterSerializer,
    DoctorActivitySerializer,
    DoctorCreateSerializer,
    DoctorManagementSerializer,
    PermissionSerializer,
    RoleSerializer,
    StaffCreateSerializer,
    StaffSerializer,
    StaffUpdateSerializer,
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


# ── Role & Permission Views ──────────────────────────────────────


@extend_schema(tags=['Permissions'])
@extend_schema_view(
    list=extend_schema(summary='List all permissions'),
    create=extend_schema(summary='Create custom permission (superadmin)'),
    partial_update=extend_schema(summary='Update permission (superadmin)'),
    destroy=extend_schema(summary='Delete custom permission (superadmin)'),
)
class PermissionViewSet(viewsets.ModelViewSet):
    """Superadmin CRUD for permissions. List is available to center admins too."""

    serializer_class = PermissionSerializer
    queryset = Permission.objects.all()
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.action == 'list':
            # Center admins can list (for role management UI)
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsSuperAdmin()]

    def perform_create(self, serializer):
        serializer.save(is_custom=True)

    def perform_destroy(self, instance):
        if not instance.is_custom:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('System permissions cannot be deleted.')
        instance.delete()


@extend_schema(tags=['Superadmin'])
class CenterListView(APIView):
    """Superadmin lists all diagnostic centers."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    @extend_schema(
        summary='List all centers (superadmin)',
        responses={200: DiagnosticCenterSerializer(many=True)},
    )
    def get(self, request):
        centers = DiagnosticCenter.objects.all().order_by('name')
        return Response(DiagnosticCenterSerializer(centers, many=True, context={'request': request}).data)


@extend_schema(tags=['Superadmin'])
class CenterPermissionView(APIView):
    """Superadmin manages available permissions per center."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    @extend_schema(
        summary='Get center available permissions',
        responses={200: PermissionSerializer(many=True)},
    )
    def get(self, request, center_id):
        try:
            center = DiagnosticCenter.objects.get(pk=center_id)
        except DiagnosticCenter.DoesNotExist:
            return Response(
                {'detail': 'Center not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        perms = center.available_permissions.all()
        return Response(PermissionSerializer(perms, many=True).data)

    @extend_schema(
        summary='Set center available permissions',
        request={'application/json': {'type': 'object', 'properties': {'permission_ids': {'type': 'array', 'items': {'type': 'integer'}}}}},
        responses={200: PermissionSerializer(many=True)},
    )
    def put(self, request, center_id):
        try:
            center = DiagnosticCenter.objects.get(pk=center_id)
        except DiagnosticCenter.DoesNotExist:
            return Response(
                {'detail': 'Center not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        perm_ids = request.data.get('permission_ids', [])
        valid_perms = Permission.objects.filter(id__in=perm_ids)
        center.available_permissions.set(valid_perms)
        logger.info(
            'Center permissions updated',
            extra={'center_id': center.id, 'perm_count': valid_perms.count()},
        )
        return Response(PermissionSerializer(center.available_permissions.all(), many=True).data)


@extend_schema_view(
    list=extend_schema(tags=["Roles"], summary="List center roles"),
    retrieve=extend_schema(tags=["Roles"], summary="Get role detail"),
    create=extend_schema(
        tags=["Roles"],
        summary="Create a new role",
        description="Admin creates a custom role with selected permissions.",
    ),
    partial_update=extend_schema(
        tags=["Roles"],
        summary="Update role",
        description="Admin updates a role's name or permissions.",
    ),
    destroy=extend_schema(
        tags=["Roles"],
        summary="Delete role",
        description="Admin deletes a custom role. System roles cannot be deleted.",
    ),
)
class RoleViewSet(viewsets.ModelViewSet):
    """CRUD for tenant-scoped roles. Admin only."""

    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        tenant = self.request.tenant
        return Role.objects.filter(center=tenant).prefetch_related('permissions')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('System roles cannot be deleted.')
        if instance.staff_members.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                'Cannot delete a role that is assigned to staff members. '
                'Reassign them first.',
            )
        instance.delete()


# ── Doctor Views ─────────────────────────────────────────────────


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
    create=extend_schema(
        tags=["Doctors"],
        summary="Register a new doctor",
        description=(
            "Admin creates a new doctor account and links it to the current center. "
            "A User record is auto-created with a generated username (dr_first_last)."
        ),
        request=DoctorCreateSerializer,
        responses={201: DoctorManagementSerializer},
    ),
    partial_update=extend_schema(
        tags=["Doctors"],
        summary="Update doctor profile",
        description="Admin updates a doctor's specialization, designation, or bio.",
    ),
    destroy=extend_schema(
        tags=["Doctors"],
        summary="Delete doctor from center",
        description=(
            "Admin deletes a doctor and their user account from the center."
        ),
    ),
)
class DoctorManagementViewSet(viewsets.ModelViewSet):
    """Admin manages doctors at their center (full CRUD)."""

    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        tenant = self.request.tenant
        return (
            Doctor.objects.filter(user__center=tenant)
            .select_related("user")
            .order_by("user__first_name")
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return DoctorCreateSerializer
        return DoctorManagementSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'activity'):
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        return [permissions.IsAuthenticated(), IsCenterAdmin()]

    def create(self, request, *args, **kwargs):
        serializer = DoctorCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()
        logger.info(
            'Doctor created and linked to center',
            extra={'doctor_id': doctor.id, 'center_id': request.tenant.id},
        )
        return Response(
            DoctorManagementSerializer(doctor).data,
            status=status.HTTP_201_CREATED,
        )

    def perform_destroy(self, instance):
        """Delete doctor and user from center."""
        tenant = self.request.tenant
        user = instance.user
        logger.info(
            'Doctor deleted from center',
            extra={'doctor_id': instance.id, 'center_id': tenant.id},
        )
        user.delete()  # cascades to delete Doctor too

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


# ── Staff Views ──────────────────────────────────────────────────


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
    create=extend_schema(
        tags=["Staff"],
        summary="Add new staff member",
        description=(
            "Create a new user and assign them as staff at the current center "
            "with the specified role."
        ),
        request=StaffCreateSerializer,
        responses={201: StaffSerializer},
    ),
    partial_update=extend_schema(
        tags=["Staff"],
        summary="Update staff role",
        description="Change a staff member's role.",
        request=StaffUpdateSerializer,
        responses={200: StaffSerializer},
    ),
    destroy=extend_schema(
        tags=["Staff"],
        summary="Remove staff member",
        description=(
            "Remove a staff member from the center. "
            "Deletes the Staff record but preserves the User account."
        ),
    ),
)
class StaffViewSet(viewsets.ModelViewSet):
    """Staff CRUD for the current center (admin use)."""

    serializer_class = StaffSerializer
    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'create':
            return StaffCreateSerializer
        if self.action == 'partial_update':
            return StaffUpdateSerializer
        return StaffSerializer

    def get_queryset(self):
        tenant = self.request.tenant
        return Staff.objects.filter(center=tenant).select_related("user", "role")

    def create(self, request, *args, **kwargs):
        serializer = StaffCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        staff = serializer.save()
        logger.info(
            'Staff member created',
            extra={'staff_id': staff.id, 'center_id': request.tenant.id},
        )
        data = StaffSerializer(staff).data
        data['generated_username'] = staff.user.username
        data['generated_password'] = serializer._generated_password
        return Response(data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = StaffUpdateSerializer(
            instance, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(StaffSerializer(instance).data)

    def perform_destroy(self, instance):
        """Remove staff record but preserve the User account."""
        if instance.user == self.request.user:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('You cannot remove yourself.')
        logger.info(
            'Staff member removed',
            extra={
                'staff_id': instance.id,
                'user_id': instance.user.id,
                'center_id': self.request.tenant.id,
            },
        )
        instance.delete()

    @extend_schema(
        tags=['Staff'],
        summary='Toggle staff active status',
        description=(
            'Activate or deactivate a staff member. '
            'Inactive users cannot log in.'
        ),
        request=None,
        responses={200: StaffSerializer},
    )
    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        staff = self.get_object()
        if staff.user == request.user:
            return Response(
                {'detail': 'You cannot deactivate yourself.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = staff.user
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        action_label = 'activated' if user.is_active else 'deactivated'
        logger.info(
            'Staff member %s', action_label,
            extra={
                'staff_id': staff.id,
                'user_id': user.id,
                'center_id': request.tenant.id,
            },
        )
        return Response(StaffSerializer(staff).data)
