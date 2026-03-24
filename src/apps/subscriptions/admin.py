from django.contrib import admin

from .models import (
    Invoice,
    PaymentInfo,
    PaymentSubmission,
    Subscription,
    SubscriptionPlan,
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "price", "max_staff", "is_active", "display_order"]
    list_filter = ["is_active"]
    ordering = ["display_order"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["center", "plan", "status", "trial_end", "billing_date"]
    list_filter = ["status", "plan"]
    search_fields = ["center__name", "center__domain"]
    raw_id_fields = ["center"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_center",
        "amount",
        "status",
        "payment_method",
        "due_date",
        "paid_at",
    ]
    list_filter = ["status", "payment_method"]
    search_fields = ["subscription__center__name"]

    @admin.display(description="Center")
    def get_center(self, obj):
        return obj.subscription.center.name


@admin.register(PaymentInfo)
class PaymentInfoAdmin(admin.ModelAdmin):
    list_display = ["label", "method", "is_active", "display_order"]
    list_filter = ["method", "is_active"]
    list_editable = ["is_active", "display_order"]
    ordering = ["display_order"]


@admin.register(PaymentSubmission)
class PaymentSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_center",
        "transaction_id",
        "status",
        "submitted_at",
        "reviewed_at",
    ]
    list_filter = ["status"]
    search_fields = [
        "transaction_id",
        "invoice__subscription__center__name",
    ]
    raw_id_fields = ["invoice", "payment_method", "submitted_by"]

    @admin.display(description="Center")
    def get_center(self, obj):
        return obj.invoice.subscription.center.name
