from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AnalyticsViewSet,
    CenterTestPricingViewSet,
    PublicReportView,
    ReferringDoctorViewSet,
    ReportTemplateViewSet,
    ReportViewSet,
    TestOrderViewSet,
    TestTypeViewSet,
)

router = DefaultRouter()
router.register(r'test-types', TestTypeViewSet, basename='test-type')
router.register(r'pricing', CenterTestPricingViewSet, basename='pricing')
router.register(r'test-orders', TestOrderViewSet, basename='test-order')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'report-templates', ReportTemplateViewSet, basename='report-template')
router.register(r'referring-doctors', ReferringDoctorViewSet, basename='referring-doctor')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('', include(router.urls)),
    path(
        'reports/public/<uuid:access_token>/',
        PublicReportView.as_view(),
        name='public-report',
    ),
]
