import logging
from decimal import Decimal

from rest_framework import serializers

from apps.diagnostics.models import CenterTestPricing, TestOrder, TestType
from apps.payments.models import Invoice, InvoiceItem

logger = logging.getLogger(__name__)


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
            "subtotal",
            "discount_percentage",
            "discount_amount",
            "total",
            "status",
            "status_display",
            "notes",
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
    """Create an invoice with line items, optional visit fee, and discount."""

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
        help_text="Auto-add doctor visit fee",
    )
    doctor_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Doctor ID — required when include_visit_fee is True",
    )
    discount_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        patient = attrs.get("patient")
        walk_in_name = attrs.get("walk_in_name", "")
        if not patient and not walk_in_name:
            raise serializers.ValidationError(
                "Either patient or walk_in_name is required."
            )
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
            appt = Appointment.objects.get(pk=value)
        except Appointment.DoesNotExist:
            raise serializers.ValidationError("Appointment not found.") from None
        if appt.center_id != tenant.id:
            raise serializers.ValidationError(
                "Appointment does not belong to this center."
            )
        return appt

    def _resolve_test_price(self, test_type, center):
        """Resolve price: CenterTestPricing → TestType.base_price fallback."""
        try:
            pricing = CenterTestPricing.objects.get(center=center, test_type=test_type)
            return pricing.price
        except CenterTestPricing.DoesNotExist:
            return test_type.base_price

    def create(self, validated_data):
        request = self.context["request"]
        tenant = request.tenant

        patient = validated_data.get("patient")
        walk_in_name = validated_data.get("walk_in_name", "")
        walk_in_phone = validated_data.get("walk_in_phone", "")
        appointment = validated_data.get("appointment")
        items_data = validated_data.get("items", [])
        include_visit_fee = validated_data["include_visit_fee"]
        discount_pct = validated_data["discount_percentage"]
        notes = validated_data.get("notes", "")

        # Create the invoice
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
        )

        # Add test / other items
        for item_data in items_data:
            item_type = item_data.get("item_type", InvoiceItem.ItemType.TEST)
            test_order_id = item_data.get("test_order_id")
            test_type_id = item_data.get("test_type_id")
            test_order = None
            description = item_data.get("description", "")
            unit_price = item_data.get("unit_price")
            quantity = item_data.get("quantity", 1)

            if item_type == InvoiceItem.ItemType.TEST:
                # Option A: from existing test order
                if test_order_id:
                    try:
                        test_order = TestOrder.objects.select_related("test_type").get(
                            pk=test_order_id, center=tenant
                        )
                    except TestOrder.DoesNotExist:
                        raise serializers.ValidationError(
                            {
                                "items": f"Test order {test_order_id} not "
                                f"found in this center."
                            }
                        ) from None
                    if not description:
                        description = test_order.test_type.name
                    if unit_price is None:
                        unit_price = self._resolve_test_price(
                            test_order.test_type, tenant
                        )

                # Option B: from test catalog (no test order)
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

        # Add visit fee if requested (per-doctor fee)
        include_visit_fee = validated_data["include_visit_fee"]
        if include_visit_fee:
            doctor_id = validated_data.get("doctor_id")
            if not doctor_id:
                raise serializers.ValidationError(
                    {"doctor_id": "Doctor is required when including visit fee."}
                )
            from core.tenants.models import Doctor

            try:
                doctor = Doctor.objects.select_related("user").get(
                    pk=doctor_id, user__center=tenant
                )
            except Doctor.DoesNotExist:
                raise serializers.ValidationError(
                    {"doctor_id": "Doctor not found in this center."}
                ) from None
            if doctor.visit_fee > 0:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    item_type=InvoiceItem.ItemType.VISIT_FEE,
                    description=f"Consultation Fee — {doctor}",
                    quantity=1,
                    unit_price=doctor.visit_fee,
                )

        # Recalculate totals
        invoice.recalculate_totals()
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
    # Print layout
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
