from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .gateway_views import InitiateChargeView, VerifyPaymentView, WebhookView
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
    # UddoktaPay gateway
    path(
        "gateway/initiate-charge/",
        InitiateChargeView.as_view(),
        name="gateway-initiate-charge",
    ),
    path(
        "gateway/verify-payment/",
        VerifyPaymentView.as_view(),
        name="gateway-verify-payment",
    ),
    path(
        "gateway/webhook/",
        WebhookView.as_view(),
        name="gateway-webhook",
    ),
]
