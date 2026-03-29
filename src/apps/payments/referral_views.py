from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.tenants.permissions import IsCenterAdmin, IsCenterStaff

from .models import Invoice, Payment, Referrer, ReferrerSettlement
from .referrer_serializers import (
    DailySummarySerializer,
    LegacyReferrerMarkPaidSerializer,
    ReferrerCreateSerializer,
    ReferrerDropdownSerializer,
    ReferrerLedgerSerializer,
    ReferrerSerializer,
    ReferrerSettlementCreateSerializer,
    ReferrerSettlementSerializer,
)
from .referrer_services import (
    ZERO,
    create_referrer_settlement,
    get_referrer_due_queryset,
)


def _build_ledger_payload(referrer, request, due_invoices=None, settlements=None):
    due_invoices = list(
        due_invoices
        if due_invoices is not None
        else get_referrer_due_queryset(referrer, request.tenant)
    )
    settlements = list(
        settlements
        if settlements is not None
        else ReferrerSettlement.objects.filter(
            referrer=referrer,
            center=request.tenant,
        ).select_related("created_by")
    )
    current_due = sum((invoice.due_amount for invoice in due_invoices), ZERO)
    total_settled = sum((settlement.amount_paid for settlement in settlements), ZERO)
    return {
        "referrer": referrer,
        "current_due": current_due,
        "due_invoice_count": len(due_invoices),
        "total_settled": total_settled,
        "due_invoices": due_invoices,
        "settlements": settlements,
    }


@extend_schema_view(
    list=extend_schema(
        tags=["Payments"],
        summary="List referrers",
        description="Returns referrers for the current center with due totals.",
    ),
    retrieve=extend_schema(
        tags=["Payments"],
        summary="Get referrer detail",
    ),
    create=extend_schema(
        tags=["Payments"],
        summary="Create a referrer",
        description="Create a payable referrer for the current center.",
        request=ReferrerCreateSerializer,
        responses={201: ReferrerSerializer},
        examples=[
            OpenApiExample(
                "Doctor referrer",
                value={
                    "name": "Dr. Aminul Islam",
                    "phone": "01710000000",
                    "type": "DOCTOR",
                    "commission_pct": "10.00",
                    "is_active": True,
                    "notes": "Outdoor prescription source",
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=["Payments"],
        summary="Update a referrer",
        description="Update a referrer profile for the current center.",
        request=ReferrerCreateSerializer,
        responses={200: ReferrerSerializer},
        examples=[
            OpenApiExample(
                "Deactivate agent",
                value={
                    "type": "AGENT",
                    "commission_pct": "8.50",
                    "is_active": False,
                    "notes": "Stopped sending patients",
                },
                request_only=True,
            ),
        ],
    ),
)
class ReferrerViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in {"create", "partial_update", "mark_paid"}:
            return [permissions.IsAuthenticated(), IsCenterAdmin()]
        if self.action == "settlements" and self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsCenterAdmin()]
        return [permissions.IsAuthenticated(), IsCenterStaff()]

    def get_queryset(self):
        queryset = Referrer.objects.filter(center=self.request.tenant)
        if self.action == "dropdown":
            queryset = queryset.filter(is_active=True)
        return queryset

    def get_serializer_class(self):
        if self.action in {"create", "partial_update"}:
            return ReferrerCreateSerializer
        if self.action == "dropdown":
            return ReferrerDropdownSerializer
        if self.action == "settlements" and self.request.method == "POST":
            return ReferrerSettlementCreateSerializer
        if self.action == "mark_paid":
            return LegacyReferrerMarkPaidSerializer
        return ReferrerSerializer

    def perform_create(self, serializer):
        serializer.save(center=self.request.tenant)

    @extend_schema(
        tags=["Payments"],
        summary="Active referrers dropdown",
        description="Returns active referrers for invoice forms.",
        responses={200: ReferrerDropdownSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        serializer = ReferrerDropdownSerializer(
            self.get_queryset(),
            many=True,
        )
        return Response(serializer.data)

    @extend_schema(
        tags=["Payments"],
        summary="Get referrer ledger",
        description="Returns current due invoices and settlement history.",
        responses={200: ReferrerLedgerSerializer},
    )
    @action(detail=True, methods=["get"], url_path="ledger")
    def ledger(self, request, pk=None):
        referrer = self.get_object()
        payload = _build_ledger_payload(referrer, request)
        return Response(
            ReferrerLedgerSerializer(
                payload,
                context={"request": request},
            ).data
        )

    @extend_schema(
        tags=["Payments"],
        summary="List or create referrer settlements",
        description=(
            "GET returns settlement history. POST creates an invoice-linked "
            "settlement for selected due invoices."
        ),
        request=ReferrerSettlementCreateSerializer,
        responses={
            200: ReferrerSettlementSerializer(many=True),
            201: ReferrerSettlementSerializer,
        },
        examples=[
            OpenApiExample(
                "Partial payout",
                value={
                    "invoice_ids": [11, 14, 18],
                    "amount_paid": "500.00",
                    "payment_method": "CASH",
                    "notes": "March payout",
                },
                request_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["get", "post"], url_path="settlements")
    def settlements(self, request, pk=None):
        referrer = self.get_object()
        if request.method == "GET":
            settlements = ReferrerSettlement.objects.filter(
                referrer=referrer,
                center=request.tenant,
            ).select_related("created_by")
            return Response(ReferrerSettlementSerializer(settlements, many=True).data)

        serializer = ReferrerSettlementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settlement = create_referrer_settlement(
            referrer=referrer,
            center=request.tenant,
            invoice_ids=serializer.validated_data["invoice_ids"],
            amount_paid=serializer.validated_data["amount_paid"],
            payment_method=serializer.validated_data["payment_method"],
            notes=serializer.validated_data.get("notes", ""),
            user=request.user,
        )
        return Response(
            ReferrerSettlementSerializer(settlement).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["Payments"],
        summary="Legacy referrer statement",
        description="Deprecated alias for the referrer ledger endpoint.",
        parameters=[
            OpenApiParameter(
                "start_date",
                str,
                required=False,
                description="Optional paid date filter (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                "end_date",
                str,
                required=False,
                description="Optional paid date filter (YYYY-MM-DD)",
            ),
        ],
        responses={200: ReferrerLedgerSerializer},
    )
    @action(detail=True, methods=["get"], url_path="statement")
    def statement(self, request, pk=None):
        referrer = self.get_object()
        due_qs = get_referrer_due_queryset(referrer, request.tenant)
        settlements = ReferrerSettlement.objects.filter(
            referrer=referrer,
            center=request.tenant,
        ).select_related("created_by")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            due_qs = due_qs.filter(paid_at__date__gte=start_date)
            settlements = settlements.filter(paid_at__date__gte=start_date)
        if end_date:
            due_qs = due_qs.filter(paid_at__date__lte=end_date)
            settlements = settlements.filter(paid_at__date__lte=end_date)
        payload = _build_ledger_payload(
            referrer,
            request,
            due_invoices=due_qs,
            settlements=settlements,
        )
        return Response(
            ReferrerLedgerSerializer(
                payload,
                context={"request": request},
            ).data
        )

    @extend_schema(
        tags=["Payments"],
        summary="Legacy mark referrer paid",
        description=(
            "Deprecated alias that settles all currently due invoices in a "
            "selected paid date range."
        ),
        request=LegacyReferrerMarkPaidSerializer,
        responses={201: ReferrerSettlementSerializer},
    )
    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        referrer = self.get_object()
        serializer = LegacyReferrerMarkPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        due_invoices = list(
            get_referrer_due_queryset(referrer, request.tenant).filter(
                paid_at__date__gte=serializer.validated_data["period_start"],
                paid_at__date__lte=serializer.validated_data["period_end"],
            )
        )
        if not due_invoices:
            return Response(
                {"detail": "No due invoices found for the selected period."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        settlement = create_referrer_settlement(
            referrer=referrer,
            center=request.tenant,
            invoice_ids=[invoice.id for invoice in due_invoices],
            amount_paid=serializer.validated_data["amount_paid"],
            payment_method=serializer.validated_data["payment_method"],
            notes=serializer.validated_data.get("notes", ""),
            user=request.user,
        )
        return Response(
            ReferrerSettlementSerializer(settlement).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["Payments"],
        summary="Legacy settlement history",
        description="Deprecated alias for GET /settlements/.",
        responses={200: ReferrerSettlementSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="payments")
    def payment_history(self, request, pk=None):
        return self.settlements(request, pk=pk)


ReferralDoctorViewSet = ReferrerViewSet


class DailySummaryView(APIView):
    """
    Daily cash register / collection summary.
    Returns aggregated invoice and payment data for a specific date.
    Admin only.
    """

    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    @extend_schema(
        tags=["Payments"],
        summary="Daily collection summary",
        description=(
            "Returns a daily summary of invoices, collections, and outstanding dues. "
            "Defaults to today if no date parameter is provided."
        ),
        parameters=[
            OpenApiParameter(
                "date",
                str,
                required=False,
                description="Date to summarize (YYYY-MM-DD, defaults to today)",
            ),
        ],
        responses={200: DailySummarySerializer},
    )
    def get(self, request):
        tenant = request.tenant
        date_str = request.query_params.get("date")

        if date_str:
            from datetime import date as date_type

            try:
                summary_date = date_type.fromisoformat(date_str)
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            summary_date = timezone.localdate()

        invoices = Invoice.objects.filter(
            center=tenant,
            created_at__date=summary_date,
        ).exclude(status=Invoice.Status.CANCELLED)

        total_invoiced = invoices.aggregate(total=Sum("total"))["total"] or ZERO

        paid_invoices = invoices.filter(status=Invoice.Status.PAID)
        paid_count = paid_invoices.count()
        unpaid_count = invoices.exclude(status=Invoice.Status.PAID).count()

        payments = Payment.objects.filter(
            appointment__center=tenant,
            created_at__date=summary_date,
            status=Payment.Status.COMPLETED,
        )

        total_collected = payments.aggregate(total=Sum("amount"))["total"] or ZERO
        paid_invoice_total = (
            paid_invoices.aggregate(total=Sum("total"))["total"] or ZERO
        )
        total_collected = max(total_collected, paid_invoice_total)

        outstanding = total_invoiced - total_collected

        by_method = defaultdict(Decimal)
        for payment in payments:
            by_method[payment.method] += payment.amount

        if not by_method and paid_invoice_total > ZERO:
            by_method["CASH"] = paid_invoice_total

        data = {
            "date": summary_date,
            "total_invoiced": total_invoiced,
            "total_collected": total_collected,
            "outstanding_dues": max(outstanding, ZERO),
            "by_method": dict(by_method),
            "invoice_count": invoices.count(),
            "paid_count": paid_count,
            "unpaid_count": unpaid_count,
        }
        return Response(DailySummarySerializer(data).data)
