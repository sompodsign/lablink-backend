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

    # Patient is required — this is who the test is for
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='test_orders',
        help_text=_('The patient this test is for'),
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
    # Appointment is optional — walk-in patients may not have one
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='test_orders',
    )
    # External referring doctor (from paper prescription)
    referring_doctor_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('Name of the external doctor who prescribed the test'),
    )
    # Which staff member created this order in the system
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_test_orders',
        help_text=_('Staff member who entered this order'),
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
        help_text=_('Notes from prescription or doctor'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'apps_test_order'
        ordering = ['-created_at']
        verbose_name = _('test order')
        verbose_name_plural = _('test orders')

    def __str__(self) -> str:
        return f'{self.test_type.name} for {self.patient.get_full_name()}'


class Report(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        VERIFIED = 'VERIFIED', _('Verified')
        DELIVERED = 'DELIVERED', _('Delivered')

    # Link to test order (primary link)
    test_order = models.OneToOneField(
        TestOrder,
        on_delete=models.CASCADE,
        related_name='report',
    )
    # Appointment is optional
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
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
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'apps_report'
        verbose_name = _('report')
        verbose_name_plural = _('reports')

    def __str__(self) -> str:
        return f'Report {self.id} - {self.test_order}'


class ReportTemplate(models.Model):
    """Defines the expected result fields for a test type.

    The `fields` JSON stores a list of field definitions, e.g.:
    [
        {"name": "Hemoglobin", "unit": "g/dL", "ref_range": "13.5-17.5"},
        {"name": "Total WBC Count", "unit": "/cumm", "ref_range": "4000-11000"},
    ]
    """

    test_type = models.OneToOneField(
        TestType,
        on_delete=models.CASCADE,
        related_name='report_template',
    )
    fields = models.JSONField(
        help_text=_(
            'List of field definitions: '
            '[{"name": "...", "unit": "...", "ref_range": "..."}]'
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'apps_report_template'
        verbose_name = _('report template')
        verbose_name_plural = _('report templates')

    def __str__(self) -> str:
        return f'Template for {self.test_type.name}'


class ReferringDoctor(models.Model):
    """Saved referring doctors for quick selection in test orders."""

    center = models.ForeignKey(
        'tenants.DiagnosticCenter',
        on_delete=models.CASCADE,
        related_name='referring_doctors',
    )
    name = models.CharField(
        max_length=255,
        help_text=_('Full name, e.g. "Dr. Aminul Islam"'),
    )
    designation = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('e.g. "MBBS, FCPS (Medicine)"'),
    )
    institution = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('e.g. "Dhaka Medical College Hospital"'),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'apps_referring_doctor'
        ordering = ['name']
        verbose_name = _('referring doctor')
        verbose_name_plural = _('referring doctors')

    def __str__(self) -> str:
        return self.name
