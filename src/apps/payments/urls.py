from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .invoice_views import InvoiceViewSet
from .referral_views import DailySummaryView, ReferrerViewSet
from .views import PaymentViewSet

router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"referrers", ReferrerViewSet, basename="referrer")
router.register(r"referral-doctors", ReferrerViewSet, basename="referral-doctor")

urlpatterns = [
    path("", include(router.urls)),
    path("daily-summary/", DailySummaryView.as_view(), name="daily-summary"),
]
