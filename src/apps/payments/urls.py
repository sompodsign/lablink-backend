from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .invoice_views import InvoiceViewSet
from .views import PaymentViewSet

router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"invoices", InvoiceViewSet, basename="invoice")

urlpatterns = [
    path("", include(router.urls)),
]
