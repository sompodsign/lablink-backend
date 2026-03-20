import logging

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.diagnostics.models import CenterTestPricing, TestOrder
from core.tenants.models import Doctor
from core.tenants.permissions import IsCenterStaff

from .invoice_serializers import (
    InvoiceCreateSerializer,
    InvoicePrintSerializer,
    InvoiceSerializer,
)
from .models import Invoice, InvoiceItem

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        tags=["Invoices"],
        summary="List invoices",
        description=(
            "Returns all invoices for the current center, "
            "ordered by most recent first. Staff only."
        ),
    ),
    retrieve=extend_schema(
        tags=["Invoices"],
        summary="Get invoice detail",
    ),
    create=extend_schema(
        tags=["Invoices"],
        summary="Create an invoice",
        description=(
            "Create an itemized invoice for a patient. "
            "Test prices are auto-resolved from center pricing. "
            "Optionally include doctor visit fee and apply a discount."
        ),
        request=InvoiceCreateSerializer,
        responses={201: InvoiceSerializer},
    ),
)
class InvoiceViewSet(viewsets.ModelViewSet):
    """
    Invoice creation, listing, and management for the current tenant center.
    Strictly scoped to staff only.
    """

    http_method_names = ["get", "post", "head", "options"]
    permission_classes = [permissions.IsAuthenticated, IsCenterStaff]

    def get_queryset(self):
        tenant = self.request.tenant
        return (
            Invoice.objects.filter(center=tenant)
            .select_related("patient", "center", "appointment")
            .prefetch_related("items__test_order__test_type")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return InvoiceCreateSerializer
        if self.action == "print_data":
            return InvoicePrintSerializer
        return InvoiceSerializer

    def create(self, request, *args, **kwargs):
        serializer = InvoiceCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save()
        return Response(
            InvoiceSerializer(invoice).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["Invoices"],
        summary="Get print-ready invoice data",
        description=(
            "Returns all data needed for printing an invoice, "
            "including center branding, patient details, and "
            "itemized breakdown with totals."
        ),
        responses={200: InvoicePrintSerializer},
    )
    @action(detail=True, methods=["get"], url_path="print")
    def print_data(self, request, pk=None):
        invoice = self.get_object()
        serializer = InvoicePrintSerializer(invoice, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        tags=["Invoices"],
        summary="Mark invoice as paid",
        description="Transition invoice status to PAID.",
        responses={200: InvoiceSerializer},
    )
    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status == Invoice.Status.CANCELLED:
            return Response(
                {"detail": "Cannot mark a cancelled invoice as paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = Invoice.Status.PAID
        invoice.save(update_fields=["status", "updated_at"])
        return Response(InvoiceSerializer(invoice).data)

    @extend_schema(
        tags=["Invoices"],
        summary="Cancel invoice",
        description="Transition invoice status to CANCELLED.",
        responses={200: InvoiceSerializer},
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status == Invoice.Status.PAID:
            return Response(
                {"detail": "Cannot cancel a paid invoice."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=["status", "updated_at"])
        return Response(InvoiceSerializer(invoice).data)

    @extend_schema(
        tags=["Invoices"],
        summary="Get uninvoiced test orders for a patient",
        description=(
            "Returns test orders not yet linked to any invoice item. "
            "Use ?patient=<id> to filter by patient."
        ),
    )
    @action(detail=False, methods=["get"], url_path="uninvoiced-orders")
    def uninvoiced_orders(self, request):
        tenant = request.tenant
        patient_id = request.query_params.get("patient")
        qs = TestOrder.objects.filter(center=tenant).exclude(
            id__in=InvoiceItem.objects.filter(
                test_order__isnull=False,
            ).values_list("test_order_id", flat=True),
        )
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        qs = qs.select_related("test_type").order_by("-created_at")
        data = [
            {
                "id": o.id,
                "test_type": o.test_type_id,
                "test_type_name": o.test_type.name,
                "patient": o.patient_id,
                "patient_name": o.patient.get_full_name() if o.patient else "",
                "status": o.status,
                "price": str(self._get_price(o, tenant)),
            }
            for o in qs.select_related("patient")
        ]
        return Response(data)

    @extend_schema(
        tags=["Invoices"],
        summary="Get test catalog with prices",
        description=(
            "Returns all available tests with center-specific pricing "
            "for the quick invoice test picker."
        ),
    )
    @action(detail=False, methods=["get"], url_path="test-catalog")
    def test_catalog(self, request):
        tenant = request.tenant
        pricing = CenterTestPricing.objects.filter(
            center=tenant, is_available=True
        ).select_related("test_type")
        tests = [
            {
                "test_type_id": p.test_type_id,
                "name": p.test_type.name,
                "price": str(p.price),
            }
            for p in pricing
        ]
        doctors = Doctor.objects.filter(
            user__center=tenant, user__is_active=True
        ).select_related("user")
        doctors_data = [
            {
                "id": d.id,
                "name": str(d),
                "visit_fee": str(d.visit_fee),
            }
            for d in doctors
        ]
        return Response(
            {
                "tests": tests,
                "doctors": doctors_data,
            }
        )

    def _get_price(self, test_order, center):
        """Resolve price from CenterTestPricing or fallback."""
        try:
            p = CenterTestPricing.objects.get(
                center=center, test_type=test_order.test_type
            )
            return p.price
        except CenterTestPricing.DoesNotExist:
            return test_order.test_type.base_price
