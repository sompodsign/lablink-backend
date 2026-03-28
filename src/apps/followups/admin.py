from django.contrib import admin

from .models import FollowUp


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = (
        "patient",
        "center",
        "doctor",
        "scheduled_date",
        "status",
        "created_by",
        "created_at",
    )
    list_filter = ("status", "center")
    search_fields = ("patient__first_name", "patient__last_name", "reason")
    raw_id_fields = ("patient", "doctor", "appointment", "created_by", "updated_by")
    date_hierarchy = "scheduled_date"
