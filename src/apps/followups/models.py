import logging
from datetime import date

from django.conf import settings
from django.db import models

from apps.appointments.models import Appointment
from core.tenants.models import DiagnosticCenter, Doctor

logger = logging.getLogger(__name__)


class FollowUp(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    center = models.ForeignKey(
        DiagnosticCenter,
        on_delete=models.CASCADE,
        related_name="followups",
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followups",
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="followups",
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="followups",
    )
    scheduled_date = models.DateField()
    reason = models.CharField(max_length=500, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    cancel_reason = models.TextField(blank=True, default="")
    notify_patient = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_followups",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_followups",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_date"]
        indexes = [
            models.Index(fields=["center", "status", "scheduled_date"]),
            models.Index(fields=["center", "patient"]),
            models.Index(fields=["center", "doctor"]),
        ]

    def __str__(self) -> str:
        return f"FollowUp({self.patient} → {self.scheduled_date} [{self.status}])"

    @property
    def is_overdue(self) -> bool:
        return self.status == self.STATUS_PENDING and self.scheduled_date < date.today()

    @property
    def is_resolved(self) -> bool:
        return self.status in (self.STATUS_COMPLETED, self.STATUS_CANCELLED)
