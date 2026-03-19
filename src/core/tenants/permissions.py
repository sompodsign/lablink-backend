import logging

from rest_framework import permissions

logger = logging.getLogger(__name__)


class IsSuperAdmin(permissions.BasePermission):
    """User must be a Django superuser (platform-level admin)."""

    message = "You must be a superadmin to perform this action."

    def has_permission(self, request, view) -> bool:
        return request.user.is_authenticated and request.user.is_superuser


class IsCenterStaff(permissions.BasePermission):
    """User must be staff at the request's tenant center."""

    message = "You must be staff at this diagnostic center."

    def has_permission(self, request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return False
        return (
            hasattr(request.user, "staff_profile")
            and request.user.staff_profile.center_id == tenant.id
        )


class IsCenterDoctor(permissions.BasePermission):
    """User must be a doctor associated with the request's tenant center."""

    message = "You must be a doctor at this diagnostic center."

    def has_permission(self, request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return False
        return hasattr(request.user, "doctor_profile") and (
            request.user.center_id == tenant.id
        )


class IsCenterAdmin(permissions.BasePermission):
    """User must be staff with manage_staff permission at the tenant center."""

    message = "You must be an admin at this diagnostic center."

    def has_permission(self, request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return False
        return (
            hasattr(request.user, "staff_profile")
            and request.user.staff_profile.center_id == tenant.id
            and request.user.staff_profile.has_perm("manage_staff")
        )


class IsCenterMedicalTechnologist(permissions.BasePermission):
    """User must be staff with create_reports permission at the tenant center."""

    message = "You must be a medical technologist at this diagnostic center."

    def has_permission(self, request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return False
        return (
            hasattr(request.user, "staff_profile")
            and request.user.staff_profile.center_id == tenant.id
            and request.user.staff_profile.has_perm("create_reports")
        )


class HasCenterPermission(permissions.BasePermission):
    """
    Generic permission check — requires a specific codename.

    Usage on views:
        permission_classes = [HasCenterPermission]
        required_permission = 'manage_payments'
    """

    message = "You do not have permission for this action."

    def has_permission(self, request, view) -> bool:
        if not request.user.is_authenticated:
            return False
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return False
        required = getattr(view, "required_permission", None)
        if not required:
            return False
        return (
            hasattr(request.user, "staff_profile")
            and request.user.staff_profile.center_id == tenant.id
            and request.user.staff_profile.has_perm(required)
        )


class IsCenterStaffOrDoctor(permissions.BasePermission):
    """User must be either staff or doctor at the tenant center."""

    message = "You must be staff or a doctor at this diagnostic center."

    def has_permission(self, request, view) -> bool:
        return IsCenterStaff().has_permission(
            request, view
        ) or IsCenterDoctor().has_permission(request, view)


class IsPatientOwner(permissions.BasePermission):
    """User must be the patient who owns the record."""

    message = "You can only access your own records."

    def has_object_permission(self, request, view, obj) -> bool:
        if not request.user.is_authenticated:
            return False
        # obj could be an Appointment, Report, or TestOrder — all have appointment.patient
        if hasattr(obj, "patient"):
            return obj.patient == request.user
        if hasattr(obj, "appointment"):
            return obj.appointment.patient == request.user
        return False
