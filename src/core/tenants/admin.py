from django.contrib import admin

from .models import DiagnosticCenter, Doctor, Service, Staff


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1
    ordering = ("order", "id")


@admin.register(DiagnosticCenter)
class DiagnosticCenterAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "domain",
        "contact_number",
        "email",
        "sms_enabled",
        "email_notifications_enabled",
        "created_at",
    )
    search_fields = ("name", "domain", "email")
    list_filter = ("sms_enabled", "email_notifications_enabled", "created_at")
    ordering = ("-created_at",)
    inlines = [ServiceInline]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "center", "icon", "order", "is_active")
    list_filter = ("center", "is_active")
    search_fields = ("title", "description", "center__name")
    ordering = ("center", "order")


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("user", "specialization", "designation")
    search_fields = ("user__username", "user__email", "specialization")


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("user", "center", "role")
    list_filter = ("center", "role")
    search_fields = ("user__username", "user__email", "center__name")
