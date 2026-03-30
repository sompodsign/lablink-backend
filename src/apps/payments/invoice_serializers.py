import logging
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.diagnostics.models import CenterTestPricing, TestOrder, TestType
from apps.payments.models import Invoice, InvoiceAuditLog, InvoiceItem, Referrer
from apps.payments.notifications import (
    send_invoice_created_email,
    send_invoice_created_sms,
)

logger = logging.getLogger(__name__)


def _build_referrer_snapshot(referrer):
    if not referrer:
        return {
            "referrer": None,
            "referrer_name_snapshot": "",
            "commission_pct_snapshot": Decimal("0.00"),
        }
    return {
        "referrer": referrer,
        "referrer_name_snapshot": referrer.name,
        "commission_pct_snapshot": referrer.commission_pct,
    }


def _extract_referrer_id(data):
    referrer_id = data.get("referrer_id")
    alias_id = data.get("referral_doctor_id")
    if referrer_id is not None and alias_id is not None and referrer_id != alias_id:
        raise serializers.ValidationError(
            {"referrer_id": "referrer_id and referral_doctor_id must match."}
        )
    return referrer_id if referrer_id is not None else alias_id


# ─── Read Serializers ─────────────────────────────────────────────


class InvoiceItemSerializer(serializers.ModelSerializer):
    item_type_display = serializers.CharField(
        source="get_item_type_display", read_only=True
    )

    class Meta:
        model = InvoiceItem
        fields = [
            "id",
            "item_type",
            "item_type_display",
            "description",
            "test_order",
            "quantity",
            "unit_price",
            "total_price",
        ]
        read_only_fields = ["id", "total_price"]


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    patient_name = serializers.SerializerMethodField()
    referrer_name = serializers.CharField(
        source="referrer_name_snapshot", read_only=True
    )
    referral_doctor = serializers.IntegerField(source="referrer_id", read_only=True)
    referral_doctor_name = serializers.CharField(
        source="referrer_name_snapshot", read_only=True
    )

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "patient",
            "patient_name",
            "walk_in_name",
            "walk_in_phone",
            "center",
            "appointment",
            "referrer",
            "referrer_name",
            "referral_doctor",
            "referral_doctor_name",
            "commission_amount",
            "subtotal",
            "discount_percentage",
            "discount_amount",
            "total",
            "status",
            "status_display",
            "notes",
            "paid_at",
            "created_by",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "invoice_number",
            "center",
            "subtotal",
            "discount_amount",
            "total",
            "commission_amount",
            "paid_at",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_patient_name(self, obj) -> str:
        if obj.patient_id:
            return obj.patient.get_full_name()
        return obj.walk_in_name or "Walk-in"


# ─── Create Serializer ────────────────────────────────────────────


class InvoiceItemInputSerializer(serializers.Serializer):
    """Input for each line item when creating an invoice."""

    test_order_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Test order ID — price resolved automatically",
    )
    test_type_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Test type ID — for catalog-based items (no test order)",
    )
    item_type = serializers.ChoiceField(
        choices=InvoiceItem.ItemType.choices,
        default=InvoiceItem.ItemType.TEST,
    )
    description = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Auto-filled for TEST items; required for OTHER items",
    )
    unit_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Auto-resolved for TEST items from center pricing",
    )
    quantity = serializers.IntegerField(default=1, min_value=1)


class InvoiceCreateSerializer(serializers.Serializer):
    """Create an invoice with line items, optional visit fee, and referrer."""

    patient = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Patient user ID (optional for walk-ins)",
    )
    walk_in_name = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        default="",
        help_text="Name for walk-in patients (no registration needed)",
    )
    walk_in_phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        default="",
        help_text="Phone for walk-in patients",
    )
    appointment = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Appointment ID (optional)",
    )
    items = InvoiceItemInputSerializer(many=True, required=False, default=list)
    include_visit_fee = serializers.BooleanField(
        default=False,
        help_text="Auto-add doctor visit fee(s)",
    )
    doctor_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Single doctor ID — backward compat, prefer doctor_ids",
    )
    doctor_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        help_text="List of doctor IDs for multi-doctor visit fees",
    )
    discount_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    referrer_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Referrer ID (canonical field)",
    )
    referral_doctor_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Deprecated alias for referrer_id",
    )

    def validate(self, attrs):
        patient = attrs.get("patient")
        walk_in_name = attrs.get("walk_in_name", "")
        if not patient and not walk_in_name:
            raise serializers.ValidationError(
                "Either patient or walk_in_name is required."
            )
        _extract_referrer_id(attrs)
        return attrs

    def validate_patient(self, value):
        if value is None:
            return None
        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            return User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Patient not found.") from None

    def validate_appointment(self, value):
        if value is None:
            return None
        from apps.appointments.models import Appointment

        tenant = self.context["request"].tenant
        try:
            appointment = Appointment.objects.get(pk=value)
        except Appointment.DoesNotExist:
            raise serializers.ValidationError("Appointment not found.") from None
        if appointment.center_id != tenant.id:
            raise serializers.ValidationError(
                "Appointment does not belong to this center."
            )
        return appointment

    def _resolve_test_price(self, test_type, center):
        try:
            pricing = CenterTestPricing.objects.get(center=center, test_type=test_type)
            return pricing.price
        except CenterTestPricing.DoesNotExist:
            return test_type.base_price

    def _resolve_referrer(self, validated_data, tenant):
        referrer_id = _extract_referrer_id(validated_data)
        if not referrer_id:
            return None
        try:
            return Referrer.objects.get(
                pk=referrer_id,
                center=tenant,
                is_active=True,
            )
        except Referrer.DoesNotExist:
            raise serializers.ValidationError(
                {"referrer_id": "Referrer not found in this center."}
            ) from None

    def _create_invoice_items(self, invoice, items_data, tenant):
        for item_data in items_data:
            item_type = item_data.get("item_type", InvoiceItem.ItemType.TEST)
            test_order_id = item_data.get("test_order_id")
            test_type_id = item_data.get("test_type_id")
            test_order = None
            description = item_data.get("description", "")
            unit_price = item_data.get("unit_price")
            quantity = item_data.get("quantity", 1)

            if item_type == InvoiceItem.ItemType.TEST:
                if test_order_id:
                    try:
                        test_order = TestOrder.objects.select_related("test_type").get(
                            pk=test_order_id,
                            center=tenant,
                        )
                    except TestOrder.DoesNotExist:
                        raise serializers.ValidationError(
                            {
                                "items": (
                                    f"Test order {test_order_id} not found in this center."
                                )
                            }
                        ) from None
                    if not description:
                        description = test_order.test_type.name
                    if unit_price is None:
                        unit_price = self._resolve_test_price(
                            test_order.test_type,
                            tenant,
                        )
                elif test_type_id:
                    try:
                        test_type = TestType.objects.get(pk=test_type_id)
                    except TestType.DoesNotExist:
                        raise serializers.ValidationError(
                            {"items": f"Test type {test_type_id} not found."}
                        ) from None
                    if not description:
                        description = test_type.name
                    if unit_price is None:
                        unit_price = self._resolve_test_price(test_type, tenant)

            if unit_price is None:
                raise serializers.ValidationError(
                    {"items": "unit_price is required for non-test items."}
                )

            InvoiceItem.objects.create(
                invoice=invoice,
                item_type=item_type,
                description=description,
                test_order=test_order,
                quantity=quantity,
                unit_price=unit_price,
            )

    def _create_visit_fee_items(self, invoice, validated_data, tenant):
        include_visit_fee = validated_data["include_visit_fee"]
        if not include_visit_fee:
            return

        from core.tenants.models import Doctor

        doctor_ids = list(validated_data.get("doctor_ids") or [])
        single_id = validated_data.get("doctor_id")
        if single_id and single_id not in doctor_ids:
            doctor_ids.append(single_id)

        if not doctor_ids:
            raise serializers.ValidationError(
                {
                    "doctor_ids": (
                        "At least one doctor is required when including visit fee."
                    )
                }
            )

        for doctor_id in doctor_ids:
            try:
                doctor = Doctor.objects.select_related("user").get(
                    pk=doctor_id,
                    user__center=tenant,
                )
            except Doctor.DoesNotExist:
                raise serializers.ValidationError(
                    {"doctor_ids": f"Doctor {doctor_id} not found in this center."}
                ) from None
            if doctor.visit_fee > 0:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    item_type=InvoiceItem.ItemType.VISIT_FEE,
                    description=f"Consultation Fee — {doctor}",
                    quantity=1,
                    unit_price=doctor.visit_fee,
                )

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        tenant = request.tenant

        patient = validated_data.get("patient")
        walk_in_name = validated_data.get("walk_in_name", "")
        walk_in_phone = validated_data.get("walk_in_phone", "")
        appointment = validated_data.get("appointment")
        items_data = validated_data.get("items", [])
        discount_pct = validated_data["discount_percentage"]
        notes = validated_data.get("notes", "")
        referrer = self._resolve_referrer(validated_data, tenant)
        snapshot = _build_referrer_snapshot(referrer)

        invoice = Invoice.objects.create(
            patient=patient,
            walk_in_name=walk_in_name,
            walk_in_phone=walk_in_phone,
            center=tenant,
            appointment=appointment,
            discount_percentage=discount_pct,
            notes=notes,
            created_by=request.user,
            status=Invoice.Status.ISSUED,
            **snapshot,
        )

        self._create_invoice_items(invoice, items_data, tenant)
        self._create_visit_fee_items(invoice, validated_data, tenant)

        invoice.recalculate_totals()

        # Trigger automated notifications based on Center Settings
        if tenant.can_use_sms and tenant.send_sms_invoice:
            send_invoice_created_sms(invoice)
        if tenant.can_use_email and tenant.send_email_invoice:
            send_invoice_created_email(invoice)

        return invoice


# ─── Print Serializer ─────────────────────────────────────────────


class InvoicePrintSerializer(serializers.ModelSerializer):
    """Returns all data needed to render a printable invoice."""

    items = InvoiceItemSerializer(many=True, read_only=True)
    patient_name = serializers.SerializerMethodField()
    patient_phone = serializers.SerializerMethodField()
    center_name = serializers.CharField(source="center.name", read_only=True)
    center_address = serializers.CharField(source="center.address", read_only=True)
    center_contact = serializers.CharField(
        source="center.contact_number", read_only=True
    )
    center_email = serializers.EmailField(source="center.email", read_only=True)
    center_logo_url = serializers.SerializerMethodField()
    center_primary_color = serializers.CharField(
        source="center.primary_color", read_only=True
    )
    paper_size = serializers.CharField(source="center.paper_size", read_only=True)
    use_preprinted_paper = serializers.BooleanField(
        source="center.use_preprinted_paper", read_only=True
    )
    print_header_margin_mm = serializers.IntegerField(
        source="center.print_header_margin_mm", read_only=True
    )
    print_footer_margin_mm = serializers.IntegerField(
        source="center.print_footer_margin_mm", read_only=True
    )

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "patient_name",
            "patient_phone",
            "walk_in_name",
            "walk_in_phone",
            "center_name",
            "center_address",
            "center_contact",
            "center_email",
            "center_logo_url",
            "center_primary_color",
            "paper_size",
            "use_preprinted_paper",
            "print_header_margin_mm",
            "print_footer_margin_mm",
            "subtotal",
            "discount_percentage",
            "discount_amount",
            "total",
            "status",
            "notes",
            "items",
            "created_at",
        ]

    def get_patient_name(self, obj) -> str:
        if obj.patient_id:
            return obj.patient.get_full_name()
        return obj.walk_in_name or "Walk-in"

    def get_patient_phone(self, obj) -> str:
        if obj.patient_id:
            return getattr(obj.patient, "phone_number", "") or ""
        return obj.walk_in_phone or ""

    def get_center_logo_url(self, obj) -> str | None:
        if obj.center.logo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.center.logo.url)
        return None


# ─── Audit Log Serializer ─────────────────────────────────────────


class InvoiceAuditLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceAuditLog
        fields = [
            "id",
            "action",
            "changes",
            "reason",
            "changed_by",
            "changed_by_name",
            "created_at",
        ]

    def get_changed_by_name(self, obj) -> str:
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.email
        return "System"


# ─── Update Serializer (PATCH) ────────────────────────────────────


class InvoiceUpdateSerializer(InvoiceCreateSerializer):
    """Update an issued invoice with audit trail support."""

    items = InvoiceItemInputSerializer(many=True, required=False)
    include_visit_fee = serializers.BooleanField(required=False, default=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    discount_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )
    reason = serializers.CharField(
        required=True,
        help_text="Reason for this edit (required for audit trail)",
    )

    def validate(self, attrs):
        _extract_referrer_id(attrs)
        return attrs

    def _snapshot_items(self, invoice):
        return [
            {
                "id": item.id,
                "item_type": item.item_type,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "total_price": str(item.total_price),
            }
            for item in invoice.items.all()
        ]

    @transaction.atomic
    def update(self, invoice, validated_data):
        request = self.context["request"]
        tenant = request.tenant
        changes = {}
        update_fields = ["updated_at"]

        if "discount_percentage" in validated_data:
            old_val = str(invoice.discount_percentage)
            new_val = str(validated_data["discount_percentage"])
            if old_val != new_val:
                changes["discount_percentage"] = {"old": old_val, "new": new_val}
                invoice.discount_percentage = validated_data["discount_percentage"]
                update_fields.append("discount_percentage")

        if "notes" in validated_data:
            old_val = invoice.notes
            new_val = validated_data["notes"]
            if old_val != new_val:
                changes["notes"] = {"old": old_val, "new": new_val}
                invoice.notes = new_val
                update_fields.append("notes")

        requested_referrer_id = _extract_referrer_id(validated_data)
        if "referrer_id" in validated_data or "referral_doctor_id" in validated_data:
            referrer = None
            if requested_referrer_id:
                referrer = self._resolve_referrer(validated_data, tenant)
            old_val = str(invoice.referrer_id) if invoice.referrer_id else None
            new_val = str(referrer.id) if referrer else None
            if old_val != new_val:
                changes["referrer"] = {"old": old_val, "new": new_val}
            snapshot = _build_referrer_snapshot(referrer)
            invoice.referrer = snapshot["referrer"]
            invoice.referrer_name_snapshot = snapshot["referrer_name_snapshot"]
            invoice.commission_pct_snapshot = snapshot["commission_pct_snapshot"]
            update_fields.extend(
                ["referrer", "referrer_name_snapshot", "commission_pct_snapshot"]
            )

        if "items" in validated_data:
            old_items = self._snapshot_items(invoice)
            invoice.items.all().delete()
            self._create_invoice_items(invoice, validated_data["items"], tenant)
            if validated_data.get("include_visit_fee"):
                self._create_visit_fee_items(invoice, validated_data, tenant)
            new_items = self._snapshot_items(invoice)
            if old_items != new_items:
                changes["items"] = {"old": old_items, "new": new_items}

        if len(update_fields) > 1:
            invoice.save(update_fields=list(dict.fromkeys(update_fields)))

        old_totals = {
            "subtotal": str(invoice.subtotal),
            "discount_amount": str(invoice.discount_amount),
            "total": str(invoice.total),
            "commission_amount": str(invoice.commission_amount),
        }
        invoice.recalculate_totals()
        new_totals = {
            "subtotal": str(invoice.subtotal),
            "discount_amount": str(invoice.discount_amount),
            "total": str(invoice.total),
            "commission_amount": str(invoice.commission_amount),
        }
        if old_totals != new_totals:
            changes["totals"] = {"old": old_totals, "new": new_totals}

        if changes:
            InvoiceAuditLog.objects.create(
                invoice=invoice,
                changed_by=request.user,
                action=InvoiceAuditLog.Action.UPDATED,
                changes=changes,
                reason=validated_data.get("reason", ""),
            )

        return invoice
