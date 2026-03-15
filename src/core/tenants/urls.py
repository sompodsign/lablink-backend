from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CurrentTenantView,
    DoctorManagementViewSet,
    PermissionListView,
    RoleViewSet,
    StaffViewSet,
)

router = DefaultRouter()
router.register(r'doctors', DoctorManagementViewSet, basename='doctor')
router.register(r'staff', StaffViewSet, basename='staff')
router.register(r'roles', RoleViewSet, basename='role')

urlpatterns = [
    path('current/', CurrentTenantView.as_view(), name='current-tenant'),
    path('permissions/', PermissionListView.as_view(), name='permission-list'),
    path('', include(router.urls)),
]
