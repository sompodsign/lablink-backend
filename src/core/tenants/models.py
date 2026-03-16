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
    available_permissions = models.ManyToManyField(
        'Permission',
        blank=True,
        related_name='available_at_centers',
        help_text=_('Permissions available to this center for building roles.'),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_('Inactive centers are blocked from all API access.'),
    )
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
    specialization = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    bio = models.TextField(blank=True)

    class Meta:
        db_table = 'core_doctor'
        verbose_name = _('doctor')
        verbose_name_plural = _('doctors')

    @property
    def center(self):
        """Convenience: doctor's center is the user's center."""
        return self.user.center

    def __str__(self) -> str:
        return f'Dr. {self.user.get_full_name()}'


class Permission(models.Model):
    """Granular permission for RBAC."""

    codename = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('Programmatic identifier, e.g. view_reports'),
    )
    name = models.CharField(
        max_length=150,
        help_text=_('Human-readable name, e.g. View Reports'),
    )
    category = models.CharField(
        max_length=50,
        help_text=_('Grouping category for UI, e.g. Reports'),
    )
    is_custom = models.BooleanField(
        default=False,
        help_text=_('True for superadmin-created permissions.'),
    )

    class Meta:
        db_table = 'core_permission'
        ordering = ['category', 'codename']
        verbose_name = _('permission')
        verbose_name_plural = _('permissions')

    def __str__(self) -> str:
        return self.codename


class Role(models.Model):
    """Tenant-scoped role with associated permissions."""

    name = models.CharField(max_length=100)
    center = models.ForeignKey(
        DiagnosticCenter,
        on_delete=models.CASCADE,
        related_name='roles',
    )
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='roles',
    )
    is_system = models.BooleanField(
        default=False,
        help_text=_('System roles cannot be deleted.'),
    )

    class Meta:
        db_table = 'core_role'
        ordering = ['name']
        unique_together = [('name', 'center')]
        verbose_name = _('role')
        verbose_name_plural = _('roles')

    def __str__(self) -> str:
        return f'{self.name} ({self.center.name})'


class Staff(models.Model):
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
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='staff_members',
    )

    class Meta:
        db_table = 'core_staff'
        ordering = ['id']
        verbose_name = _('staff')
        verbose_name_plural = _('staff')

    def __str__(self) -> str:
        return f'{self.user.get_full_name()} - {self.role.name}'

    @property
    def role_name(self) -> str:
        return self.role.name

    def has_perm(self, codename: str) -> bool:
        """Check if this staff member's role includes the given permission."""
        return self.role.permissions.filter(codename=codename).exists()

    def get_role_display(self) -> str:
        return self.role.name

