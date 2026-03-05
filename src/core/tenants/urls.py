from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CurrentTenantView, DoctorManagementViewSet, StaffViewSet

router = DefaultRouter()
router.register(r'doctors', DoctorManagementViewSet, basename='doctor')
router.register(r'staff', StaffViewSet, basename='staff')

urlpatterns = [
    path('current/', CurrentTenantView.as_view(), name='current-tenant'),
    path('', include(router.urls)),
]
