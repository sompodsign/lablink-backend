from django.contrib import admin

from .models import CenterTestPricing, Report, TestOrder, TestType


@admin.register(TestType)
class TestTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_price')
    search_fields = ('name', 'description')


@admin.register(CenterTestPricing)
class CenterTestPricingAdmin(admin.ModelAdmin):
    list_display = ('center', 'test_type', 'price', 'is_available')
    list_filter = ('center', 'is_available')
    search_fields = ('test_type__name', 'center__name')


@admin.register(TestOrder)
class TestOrderAdmin(admin.ModelAdmin):
    list_display = (
        'test_type',
        'get_patient',
        'center',
        'status',
        'priority',
        'ordered_by',
        'created_at',
    )
    list_filter = ('status', 'priority', 'center', 'created_at')
    search_fields = (
        'test_type__name',
        'appointment__patient__first_name',
        'appointment__patient__last_name',
    )
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Patient')
    def get_patient(self, obj) -> str:
        return obj.appointment.patient.get_full_name()


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_patient',
        'test_type',
        'status',
        'verified_by',
        'is_delivered_online',
        'created_at',
    )
    list_filter = ('status', 'is_delivered_online', 'created_at')
    search_fields = (
        'test_type__name',
        'appointment__patient__first_name',
        'appointment__patient__last_name',
    )
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Patient')
    def get_patient(self, obj) -> str:
        return obj.appointment.patient.get_full_name()
