from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from core.users.models import User


class DiagnosticCenter(models.Model):
    name = models.CharField(max_length=255)
    domain = models.CharField(
        max_length=100,
        unique=True,
        default='demo',
        help_text=_("Subdomain identifier, e.g., 'popularhospital'"),
    )
    tagline = models.CharField(
        max_length=255,
        blank=True,
        default='Your trusted diagnostic partner',
    )
    address = models.TextField()
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    logo = models.ImageField(upload_to='center_logos/', blank=True, null=True)
    primary_color = models.CharField(
        max_length=7,
        default='#0d9488',
        help_text=_('Hex color code'),
    )

    # Stats / Hero content
    years_of_experience = models.CharField(max_length=50, default='15+')
    happy_patients_count = models.CharField(max_length=50, default='50,000+')
    test_types_available_count = models.CharField(max_length=50, default='100+')
    lab_support_availability = models.CharField(max_length=50, default='24/7')

    opening_hours = models.CharField(max_length=100, default='8:00 AM - 10:00 PM')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_diagnostic_center'
        verbose_name = _('diagnostic center')
        verbose_name_plural = _('diagnostic centers')

    def __str__(self) -> str:
        return str(self.name)


class Service(models.Model):
    center = models.ForeignKey(
        DiagnosticCenter,
        on_delete=models.CASCADE,
        related_name='services',
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(
        max_length=10,
        default='🩺',
        help_text=_('Emoji or icon character'),
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text=_('Display order on the landing page'),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'core_service'
        ordering = ['order', 'id']
        verbose_name = _('service')
        verbose_name_plural = _('services')

    def __str__(self) -> str:
        return f'{self.title} - {self.center.name}'


class Doctor(models.Model):
    user: 'User' = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_profile',
    )  # type: ignore[assignment]
    centers = models.ManyToManyField(
        DiagnosticCenter,
        related_name='doctors',
    )
    specialization = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    bio = models.TextField(blank=True)

    class Meta:
        db_table = 'core_doctor'
        verbose_name = _('doctor')
        verbose_name_plural = _('doctors')

    def __str__(self) -> str:
        return f'Dr. {self.user.get_full_name()}'


class Staff(models.Model):
    class Role(models.TextChoices):
        RECEPTIONIST = 'RECEPTIONIST', _('Receptionist')
        LAB_TECHNICIAN = 'LAB_TECHNICIAN', _('Lab Technician')
        ADMIN = 'ADMIN', _('Admin')

    user: 'User' = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_profile',
    )  # type: ignore[assignment]
    center = models.ForeignKey(
        DiagnosticCenter,
        on_delete=models.CASCADE,
        related_name='staff',
    )
    role = models.CharField(max_length=50, choices=Role.choices)

    class Meta:
        db_table = 'core_staff'
        ordering = ['id']
        verbose_name = _('staff')
        verbose_name_plural = _('staff')

    def __str__(self) -> str:
        return f'{self.user.get_full_name()} - {self.role}'
