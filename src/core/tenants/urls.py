from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .superadmin_views import (
    SuperadminCenterDetailView,
    SuperadminCenterListView,
    SuperadminCenterRolesView,
    SuperadminCenterToggleView,
    SuperadminDashboardView,
    SuperadminDoctorListView,
    SuperadminPatientListView,
    SuperadminStaffListView,
    SuperadminUserDetailView,
    SuperadminUserListView,
)
from .views import (
    CenterListView,
    CenterPermissionView,
    CenterSettingsView,
    CurrentTenantView,
    DoctorManagementViewSet,
    PermissionViewSet,
    RoleViewSet,
    StaffViewSet,
    TenantByDomainView,
)

router = DefaultRouter()
router.register(r"doctors", DoctorManagementViewSet, basename="doctor")
router.register(r"staff", StaffViewSet, basename="staff")
router.register(r"roles", RoleViewSet, basename="role")
router.register(r"permissions", PermissionViewSet, basename="permission")

superadmin_patterns = [
    path("dashboard/", SuperadminDashboardView.as_view(), name="sa-dashboard"),
    path("centers/", SuperadminCenterListView.as_view(), name="sa-centers"),
    path(
        "centers/<int:center_id>/",
        SuperadminCenterDetailView.as_view(),
        name="sa-center-detail",
    ),
    path(
        "centers/<int:center_id>/toggle-active/",
        SuperadminCenterToggleView.as_view(),
        name="sa-center-toggle",
    ),
    path("users/", SuperadminUserListView.as_view(), name="sa-users"),
    path(
        "users/<int:user_id>/",
        SuperadminUserDetailView.as_view(),
        name="sa-user-detail",
    ),
    path("patients/", SuperadminPatientListView.as_view(), name="sa-patients"),
    path("staff/", SuperadminStaffListView.as_view(), name="sa-staff"),
    path("doctors/", SuperadminDoctorListView.as_view(), name="sa-doctors"),
    path(
        "centers/<int:center_id>/roles/",
        SuperadminCenterRolesView.as_view(),
        name="sa-center-roles",
    ),
]

urlpatterns = [
    path("current/", CurrentTenantView.as_view(), name="current-tenant"),
    path("settings/", CenterSettingsView.as_view(), name="center-settings"),
    path("by-domain/", TenantByDomainView.as_view(), name="tenant-by-domain"),
    path("centers/", CenterListView.as_view(), name="center-list"),
    path(
        "centers/<int:center_id>/permissions/",
        CenterPermissionView.as_view(),
        name="center-permissions",
    ),
    path("superadmin/", include(superadmin_patterns)),
    path("", include(router.urls)),
]
