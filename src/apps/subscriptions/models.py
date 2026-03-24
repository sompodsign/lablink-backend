from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SubscriptionPlan(models.Model):
    """Defines a subscription tier (Starter, Professional, Enterprise)."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, help_text=_("URL-safe identifier"))
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Monthly price in BDT"),
    )
    trial_days = models.IntegerField(
        default=14,
        help_text=_("Number of free trial days"),
    )
    max_staff = models.IntegerField(
        default=-1,
        help_text=_("-1 means unlimited"),
    )
    max_reports = models.IntegerField(
        default=-1,
        help_text=_("Monthly report limit, -1 means unlimited"),
    )
    features = models.JSONField(
        default=list,
        help_text=_("List of feature strings for display"),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Available for new subscriptions"),
    )
    display_order = models.IntegerField(
        default=0,
        help_text=_("Ordering on pricing page"),
    )

    class Meta:
        db_table = "apps_subscription_plan"
        ordering = ["display_order"]
        verbose_name = _("subscription plan")
        verbose_name_plural = _("subscription plans")

    def __str__(self) -> str:
        return f"{self.name} (৳{self.price}/mo)"


class Subscription(models.Model):
    """Tracks a center's active subscription and billing state."""

    class Status(models.TextChoices):
        TRIAL = "TRIAL", _("Trial")
        INACTIVE = "INACTIVE", _("Inactive")
        ACTIVE = "ACTIVE", _("Active")
        EXPIRED = "EXPIRED", _("Expired")
        CANCELLED = "CANCELLED", _("Cancelled")

    center = models.OneToOneField(
        "tenants.DiagnosticCenter",
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRIAL,
    )
    trial_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the trial period started"),
    )
    trial_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the trial period expires"),
    )
    billing_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Next billing date"),
    )
    started_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "apps_subscription"
        verbose_name = _("subscription")
        verbose_name_plural = _("subscriptions")

    def __str__(self) -> str:
        return f"{self.center.name} - {self.plan.name} ({self.status})"

    @property
    def is_trial_expired(self) -> bool:
        if self.status != self.Status.TRIAL:
            return False
        if not self.trial_end:
            return False
        return timezone.now() >= self.trial_end

    @property
    def days_remaining_trial(self) -> int | None:
        if self.status != self.Status.TRIAL or not self.trial_end:
            return None
        delta = self.trial_end - timezone.now()
        return max(0, delta.days)


class Invoice(models.Model):
    """Billing invoice for a subscription period."""

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        PAID = "PAID", _("Paid")
        OVERDUE = "OVERDUE", _("Overdue")
        CANCELLED = "CANCELLED", _("Cancelled")

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", _("Cash")
        BKASH = "BKASH", _("bKash")
        NAGAD = "NAGAD", _("Nagad")
        ONLINE = "ONLINE", _("Online Gateway")
        BANK_TRANSFER = "BANK_TRANSFER", _("Bank Transfer")

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        blank=True,
    )
    due_date = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "apps_invoice"
        ordering = ["-created_at"]
        verbose_name = _("invoice")
        verbose_name_plural = _("invoices")

    def __str__(self) -> str:
        return (
            f"Invoice #{self.id} - {self.subscription.center.name}"
            f" - ৳{self.amount} ({self.status})"
        )


class PaymentInfo(models.Model):
    """Payment method details shown on the paywall (bKash, bank, etc.)."""

    class Method(models.TextChoices):
        BKASH = "BKASH", _("bKash")
        NAGAD = "NAGAD", _("Nagad")
        ROCKET = "ROCKET", _("Rocket")
        BANK_TRANSFER = "BANK_TRANSFER", _("Bank Transfer")
        OTHER = "OTHER", _("Other")

    method = models.CharField(
        max_length=30,
        choices=Method.choices,
    )
    label = models.CharField(
        max_length=200,
        help_text=_("Display label, e.g. 'bKash Send Money'"),
    )
    details = models.TextField(
        help_text=_("Payment details — number, account name, branch, etc."),
    )
    icon = models.CharField(
        max_length=10,
        blank=True,
        help_text=_("Emoji or short icon text"),
    )
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "apps_payment_info"
        ordering = ["display_order"]
        verbose_name = _("payment info")
        verbose_name_plural = _("payment info")

    def __str__(self) -> str:
        return f"{self.label} ({self.get_method_display()})"


class PaymentSubmission(models.Model):
    """Payment proof submitted by a center admin for invoice verification."""

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending Review")
        VERIFIED = "VERIFIED", _("Verified")
        REJECTED = "REJECTED", _("Rejected")

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payment_submissions",
    )
    payment_method = models.ForeignKey(
        PaymentInfo,
        on_delete=models.SET_NULL,
        null=True,
    )
    transaction_id = models.CharField(max_length=100)
    submitted_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    admin_notes = models.TextField(
        blank=True,
        help_text=_("Rejection reason or admin comments"),
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "apps_payment_submission"
        ordering = ["-submitted_at"]
        verbose_name = _("payment submission")
        verbose_name_plural = _("payment submissions")

    def __str__(self) -> str:
        return f"Submission #{self.id} - {self.transaction_id} ({self.status})"
