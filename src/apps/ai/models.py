import logging

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class AICreditUsageLog(models.Model):
    """Tracks every AI credit deduction for audit and transparency."""

    class TaskType(models.TextChoices):
        REPORT_EXTRACTION = "REPORT_EXTRACTION", _("Report Extraction")
        CHATBOT_SESSION = "CHATBOT_SESSION", _("Chatbot Session")

    center = models.ForeignKey(
        "tenants.DiagnosticCenter",
        on_delete=models.CASCADE,
        related_name="ai_credit_logs",
    )
    task_type = models.CharField(
        max_length=30,
        choices=TaskType.choices,
    )
    credits_used = models.IntegerField(
        default=1,
        help_text=_("Number of credits consumed by this task"),
    )
    input_tokens = models.IntegerField(
        default=0,
        help_text=_("Tokens sent to the AI model"),
    )
    output_tokens = models.IntegerField(
        default=0,
        help_text=_("Tokens received from the AI model"),
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Extra context: report_id, test_type, etc."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "apps_ai_credit_usage_log"
        ordering = ["-created_at"]
        verbose_name = _("AI credit usage log")
        verbose_name_plural = _("AI credit usage logs")

    def __str__(self) -> str:
        return (
            f"{self.get_task_type_display()} - "
            f"{self.credits_used} credit(s) - {self.center}"
        )
