from django.contrib import admin

from .models import Invoice, Subscription, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price', 'max_staff', 'is_active', 'display_order']
    list_filter = ['is_active']
    ordering = ['display_order']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['center', 'plan', 'status', 'trial_end', 'billing_date']
    list_filter = ['status', 'plan']
    search_fields = ['center__name', 'center__domain']
    raw_id_fields = ['center']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'get_center',
        'amount',
        'status',
        'payment_method',
        'due_date',
        'paid_at',
    ]
    list_filter = ['status', 'payment_method']
    search_fields = ['subscription__center__name']

    @admin.display(description='Center')
    def get_center(self, obj):
        return obj.subscription.center.name
