from django.contrib import admin

from .models import AICreditUsageLog


@admin.register(AICreditUsageLog)
class AICreditUsageLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "center",
        "task_type",
        "credits_used",
        "performed_by",
        "created_at",
    )
    list_filter = ("task_type", "created_at")
    search_fields = ("center__name",)
    readonly_fields = (
        "center",
        "task_type",
        "credits_used",
        "input_tokens",
        "output_tokens",
        "performed_by",
        "metadata",
        "created_at",
    )
    ordering = ("-created_at",)
