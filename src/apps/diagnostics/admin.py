from django.contrib import admin

from .models import CenterTestPricing, ReferringDoctor, Report, ReportTemplate, TestOrder, TestType


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
        'patient',
        'center',
        'status',
        'priority',
        'referring_doctor_name',
        'created_by',
        'created_at',
    )
    list_filter = ('status', 'priority', 'center', 'created_at')
    search_fields = (
        'test_type__name',
        'patient__first_name',
        'patient__last_name',
        'referring_doctor_name',
    )
    readonly_fields = ('created_at', 'updated_at')


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
        'test_order__patient__first_name',
        'test_order__patient__last_name',
    )
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Patient')
    def get_patient(self, obj) -> str:
        return obj.test_order.patient.get_full_name()


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('test_type', 'center', 'created_at', 'updated_at')
    list_filter = ('center',)
    search_fields = ('test_type__name', 'center__name')


@admin.register(ReferringDoctor)
class ReferringDoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'designation', 'institution', 'center', 'is_active')
    list_filter = ('center', 'is_active')
    search_fields = ('name', 'designation', 'institution')
