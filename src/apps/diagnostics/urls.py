from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CenterTestPricingViewSet, ReportViewSet, TestOrderViewSet, TestTypeViewSet

router = DefaultRouter()
router.register(r'test-types', TestTypeViewSet, basename='test-type')
router.register(r'pricing', CenterTestPricingViewSet, basename='pricing')
router.register(r'test-orders', TestOrderViewSet, basename='test-order')
router.register(r'reports', ReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
]
