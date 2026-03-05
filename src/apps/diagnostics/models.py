from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class TestType(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # Base price can be overridden by center pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'apps_test_type'
        verbose_name = _('test type')
        verbose_name_plural = _('test types')

    def __str__(self) -> str:
        return self.name


class CenterTestPricing(models.Model):
    center = models.ForeignKey(
        'tenants.DiagnosticCenter',
        on_delete=models.CASCADE,
        related_name='test_pricings',
    )
    test_type = models.ForeignKey(
        TestType,
        on_delete=models.CASCADE,
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)

    class Meta:
        db_table = 'apps_center_test_pricing'
        unique_together = ('center', 'test_type')
        verbose_name = _('center test pricing')
        verbose_name_plural = _('center test pricings')

    def __str__(self) -> str:
        return f'{self.center} - {self.test_type} - {self.price}'


class TestOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')

    class Priority(models.TextChoices):
        NORMAL = 'NORMAL', _('Normal')
        URGENT = 'URGENT', _('Urgent')

    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.CASCADE,
        related_name='test_orders',
    )
    center = models.ForeignKey(
        'tenants.DiagnosticCenter',
        on_delete=models.CASCADE,
        related_name='test_orders',
    )
    test_type = models.ForeignKey(
        TestType,
        on_delete=models.PROTECT,
    )
    ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordered_tests',
        help_text=_('The doctor who ordered this test'),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    clinical_notes = models.TextField(
        blank=True,
        help_text=_('Doctor notes for the lab technician'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'apps_test_order'
        ordering = ['-created_at']
        verbose_name = _('test order')
        verbose_name_plural = _('test orders')

    def __str__(self) -> str:
        patient = self.appointment.patient
        return f'{self.test_type.name} for {patient.get_full_name()}'


class Report(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        VERIFIED = 'VERIFIED', _('Verified')
        DELIVERED = 'DELIVERED', _('Delivered')

    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.CASCADE,
        related_name='reports',
    )
    test_order = models.OneToOneField(
        TestOrder,
        on_delete=models.CASCADE,
        related_name='report',
        null=True,
        blank=True,
        help_text=_('The test order this report fulfills'),
    )
    test_type = models.ForeignKey(
        TestType,
        on_delete=models.PROTECT,
    )
    file = models.FileField(upload_to='reports/', blank=True, null=True)
    result_text = models.TextField(
        blank=True,
        help_text=_('Free-text test result entered by the technologist'),
    )
    result_data = models.JSONField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_reports',
    )
    is_delivered_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'apps_report'
        verbose_name = _('report')
        verbose_name_plural = _('reports')

    def __str__(self) -> str:
        return f'Report {self.id} - {self.appointment}'
