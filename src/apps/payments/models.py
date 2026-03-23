import logging
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.appointments.models import Appointment

logger = logging.getLogger(__name__)


# ─── Invoice ──────────────────────────────────────────────────────


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        ISSUED = "ISSUED", _("Issued")
        PAID = "PAID", _("Paid")
        CANCELLED = "CANCELLED", _("Cancelled")

    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        help_text=_("Auto-generated invoice number"),
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoices",
        null=True,
        blank=True,
        help_text=_("Registered patient (optional for walk-ins)"),
    )
    walk_in_name = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Name for walk-in patients (no registration)"),
    )
    walk_in_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Phone for walk-in patients"),
    )
    center = models.ForeignKey(
        "tenants.DiagnosticCenter",
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Sum of all line-item totals before discount"),
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Discount percentage (0-100)"),
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Computed: subtotal × discount_percentage / 100"),
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Computed: subtotal − discount_amount"),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_invoices",
        help_text=_("Staff member who created this invoice"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "apps_billing_invoice"
        ordering = ["-created_at"]
        verbose_name = _("invoice")
        verbose_name_plural = _("invoices")

    def __str__(self) -> str:
        name = (
            self.patient.get_full_name()
            if self.patient
            else self.walk_in_name or "Walk-in"
        )
        return f"{self.invoice_number} — {name}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.patient_id and not self.walk_in_name:
            raise ValidationError(_("Either patient or walk_in_name is required."))

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self._generate_invoice_number()
        super().save(*args, **kwargs)

    def _generate_invoice_number(self) -> str:
        """Generate INV-YYYYMMDD-XXXX sequential invoice number."""
        from django.utils import timezone

        today = timezone.localdate()
        prefix = f"INV-{today:%Y%m%d}-"
        last = (
            Invoice.objects.filter(invoice_number__startswith=prefix)
            .order_by("-invoice_number")
            .values_list("invoice_number", flat=True)
            .first()
        )
        seq = int(last.split("-")[-1]) + 1 if last else 1
        return f"{prefix}{seq:04d}"

    def recalculate_totals(self):
        """Recalculate subtotal, discount_amount, and total from items."""
        self.subtotal = sum(item.total_price for item in self.items.all()) or Decimal(
            "0.00"
        )
        self.discount_amount = (
            self.subtotal * self.discount_percentage / Decimal("100")
        ).quantize(Decimal("0.01"))
        self.total = self.subtotal - self.discount_amount
        self.save(update_fields=["subtotal", "discount_amount", "total"])


# ─── Invoice Items ────────────────────────────────────────────────


class InvoiceItem(models.Model):
    class ItemType(models.TextChoices):
        TEST = "TEST", _("Diagnostic Test")
        VISIT_FEE = "VISIT_FEE", _("Doctor Visit Fee")
        OTHER = "OTHER", _("Other")

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
    )
    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
    )
    description = models.CharField(max_length=255)
    test_order = models.ForeignKey(
        "diagnostics.TestOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_items",
        help_text=_("Link to test order (for TEST items)"),
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("quantity × unit_price"),
    )

    class Meta:
        db_table = "apps_billing_invoice_item"
        verbose_name = _("invoice item")
        verbose_name_plural = _("invoice items")

    def __str__(self) -> str:
        return f"{self.description} — ৳{self.total_price}"

    def save(self, *args, **kwargs):
        from decimal import Decimal

        self.total_price = Decimal(str(self.unit_price)) * self.quantity
        super().save(*args, **kwargs)


# ─── Payment ─────────────────────────────────────────────────────


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "CASH", _("Cash")
        CARD = "CARD", _("Card")
        MOBILE_BANKING = "MOBILE_BANKING", _("Mobile Banking")
        ONLINE = "ONLINE", _("Online Gateway")

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Failed")

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        help_text=_("Invoice this payment is for"),
    )
    test_order = models.ForeignKey(
        "diagnostics.TestOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        help_text=_("Optional: link payment to a specific test order"),
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    method = models.CharField(max_length=50, choices=Method.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "apps_payment"
        verbose_name = _("payment")
        verbose_name_plural = _("payments")

    def __str__(self) -> str:
        return f"{self.appointment} - {self.amount} - {self.status}"


# ─── Invoice Audit Log ───────────────────────────────────────────


class InvoiceAuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = 'CREATED', _('Created')
        UPDATED = 'UPDATED', _('Updated')
        STATUS_CHANGED = 'STATUS_CHANGED', _('Status Changed')

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='audit_logs',
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_audit_logs',
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
    )
    changes = models.JSONField(
        default=dict,
        help_text=_('JSON diff: {"field": {"old": x, "new": y}, ...}'),
    )
    reason = models.TextField(
        blank=True,
        help_text=_('Reason for the change'),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'apps_billing_invoice_audit_log'
        ordering = ['-created_at']
        verbose_name = _('invoice audit log')
        verbose_name_plural = _('invoice audit logs')

    def __str__(self) -> str:
        return f'{self.invoice.invoice_number} — {self.action} by {self.changed_by}'
