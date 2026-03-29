import logging
from decimal import Decimal

from rest_framework import serializers

from apps.payments.models import Referrer, ReferrerSettlement
from apps.payments.referrer_services import (
    ZERO,
    get_referrer_due_queryset,
)

logger = logging.getLogger(__name__)


class ReferrerSerializer(serializers.ModelSerializer):
    current_due = serializers.SerializerMethodField()
    total_settled = serializers.SerializerMethodField()
    due_invoice_count = serializers.SerializerMethodField()

    class Meta:
        model = Referrer
        fields = [
            "id",
            "name",
            "phone",
            "type",
            "commission_pct",
            "is_active",
            "notes",
            "current_due",
            "total_settled",
            "due_invoice_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def _get_due_queryset(self, obj):
        request = self.context.get("request")
        if not request:
            return obj.invoices.none()
        return get_referrer_due_queryset(obj, request.tenant)

    def get_current_due(self, obj) -> str:
        total = sum(
            (invoice.due_amount for invoice in self._get_due_queryset(obj)),
            ZERO,
        )
        return str(total.quantize(Decimal("0.01")))

    def get_total_settled(self, obj) -> str:
        request = self.context.get("request")
        if not request:
            return str(ZERO.quantize(Decimal("0.01")))
        total = obj.settlements.filter(center=request.tenant).values_list(
            "amount_paid", flat=True
        )
        return str(sum(total, ZERO).quantize(Decimal("0.01")))

    def get_due_invoice_count(self, obj) -> int:
        return self._get_due_queryset(obj).count()


class ReferrerCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referrer
        fields = [
            "name",
            "phone",
            "type",
            "commission_pct",
            "is_active",
            "notes",
        ]

    def validate_commission_pct(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Commission percentage must be between 0 and 100."
            )
        return value


class ReferrerDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referrer
        fields = ["id", "name", "type", "commission_pct"]


class ReferrerDueInvoiceSerializer(serializers.Serializer):
    invoice_id = serializers.IntegerField(source="id")
    invoice_number = serializers.CharField()
    patient_name = serializers.SerializerMethodField()
    paid_at = serializers.DateTimeField()
    invoice_total = serializers.DecimalField(
        source="total",
        max_digits=10,
        decimal_places=2,
    )
    commission_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    settled_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    due_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    def get_patient_name(self, obj) -> str:
        if obj.patient_id:
            return obj.patient.get_full_name()
        return obj.walk_in_name or "Walk-in"


class ReferrerSettlementSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ReferrerSettlement
        fields = [
            "id",
            "settlement_number",
            "amount_paid",
            "payment_method",
            "paid_at",
            "notes",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "settlement_number", "created_by", "created_at"]

    def get_created_by_name(self, obj) -> str:
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return ""


class ReferrerLedgerSerializer(serializers.Serializer):
    referrer = ReferrerSerializer()
    current_due = serializers.DecimalField(max_digits=10, decimal_places=2)
    due_invoice_count = serializers.IntegerField()
    total_settled = serializers.DecimalField(max_digits=10, decimal_places=2)
    due_invoices = ReferrerDueInvoiceSerializer(many=True)
    settlements = ReferrerSettlementSerializer(many=True)


class ReferrerSettlementCreateSerializer(serializers.Serializer):
    invoice_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )
    amount_paid = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    payment_method = serializers.ChoiceField(
        choices=ReferrerSettlement.PaymentMethod.choices,
        default=ReferrerSettlement.PaymentMethod.CASH,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class LegacyReferrerMarkPaidSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    amount_paid = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    payment_method = serializers.ChoiceField(
        choices=ReferrerSettlement.PaymentMethod.choices,
        default=ReferrerSettlement.PaymentMethod.CASH,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["period_start"] > attrs["period_end"]:
            raise serializers.ValidationError("period_start must be before period_end.")
        return attrs


class DailySummarySerializer(serializers.Serializer):
    """Read-only serializer for the daily cash register summary."""

    date = serializers.DateField()
    total_invoiced = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_collected = serializers.DecimalField(max_digits=12, decimal_places=2)
    outstanding_dues = serializers.DecimalField(max_digits=12, decimal_places=2)
    by_method = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2)
    )
    invoice_count = serializers.IntegerField()
    paid_count = serializers.IntegerField()
    unpaid_count = serializers.IntegerField()
