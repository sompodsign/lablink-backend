from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from core.users.models import User


class LanguageChoices(models.TextChoices):
    ENGLISH = "en", _("English")
    BENGALI = "bn", _("Bengali")


class DiagnosticCenter(models.Model):
    name = models.CharField(max_length=255)
    domain = models.CharField(
        max_length=100,
        unique=True,
        default="demo",
        help_text=_("Subdomain identifier, e.g., 'popularhospital'"),
    )
    language = models.CharField(
        max_length=5,
        choices=LanguageChoices.choices,
        default=LanguageChoices.ENGLISH,
        help_text=_("Language for this center's public pages and dashboard"),
    )
    tagline = models.CharField(
        max_length=255,
        blank=True,
        default="Your trusted diagnostic partner",
    )
    tagline_bn = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Bengali translation of the tagline"),
    )
    address = models.TextField()
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    logo = models.ImageField(upload_to="center_logos/", blank=True, null=True)
    primary_color = models.CharField(
        max_length=7,
        default="#0d9488",
        help_text=_("Hex color code"),
    )

    # Stats / Hero content
    years_of_experience = models.CharField(max_length=50, default="15+")
    happy_patients_count = models.CharField(max_length=50, default="50,000+")
    test_types_available_count = models.CharField(max_length=50, default="100+")
    lab_support_availability = models.CharField(max_length=50, default="24/7")

    opening_hours = models.CharField(max_length=100, default="8:00 AM - 10:00 PM")
    available_permissions = models.ManyToManyField(
        "Permission",
        blank=True,
        related_name="available_at_centers",
        help_text=_("Permissions available to this center for building roles."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Inactive centers are blocked from all API access."),
    )
    allow_online_appointments = models.BooleanField(
        default=False,
        help_text=_("Whether patients can self-book appointments online."),
    )
    doctor_visit_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Default doctor consultation / visit fee for this center"),
    )

    # ── Print Layout ──────────────────────────────────────────────
    class PaperSize(models.TextChoices):
        A4 = "A4", _("A4 (210 × 297 mm)")
        A5 = "A5", _("A5 (148 × 210 mm)")
        LETTER = "Letter", _("Letter (216 × 279 mm)")

    paper_size = models.CharField(
        max_length=10,
        choices=PaperSize.choices,
        default=PaperSize.A4,
        help_text=_("Paper size for printing invoices and reports"),
    )
    use_preprinted_paper = models.BooleanField(
        default=False,
        help_text=_(
            "Hide digital header/footer when printing "
            "(for pre-printed letterhead paper)"
        ),
    )
    print_header_margin_mm = models.PositiveIntegerField(
        default=0,
        help_text=_("Top margin in mm to skip for pre-printed header"),
    )
    print_footer_margin_mm = models.PositiveIntegerField(
        default=0,
        help_text=_("Bottom margin in mm to skip for pre-printed footer"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_diagnostic_center"
        verbose_name = _("diagnostic center")
        verbose_name_plural = _("diagnostic centers")

    def __str__(self) -> str:
        return str(self.name)


class Service(models.Model):
    center = models.ForeignKey(
        DiagnosticCenter,
        on_delete=models.CASCADE,
        related_name="services",
    )
    title = models.CharField(max_length=100)
    title_bn = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=_("Bengali translation of the title"),
    )
    description = models.TextField()
    description_bn = models.TextField(
        blank=True,
        default="",
        help_text=_("Bengali translation of the description"),
    )
    icon = models.CharField(
        max_length=10,
        default="🩺",
        help_text=_("Emoji or icon character"),
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order on the landing page"),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_service"
        ordering = ["order", "id"]
        verbose_name = _("service")
        verbose_name_plural = _("services")

    def __str__(self) -> str:
        return f"{self.title} - {self.center.name}"


class Doctor(models.Model):
    user: "User" = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
    )  # type: ignore[assignment]
    specialization = models.CharField(max_length=255)
    specialization_bn = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Bengali translation of specialization"),
    )
    designation = models.CharField(max_length=255)
    designation_bn = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Bengali translation of designation"),
    )
    bio = models.TextField(blank=True)
    bio_bn = models.TextField(
        blank=True,
        default="",
        help_text=_("Bengali translation of bio"),
    )
    visit_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Doctor consultation / visit fee"),
    )

    class Meta:
        db_table = "core_doctor"
        verbose_name = _("doctor")
        verbose_name_plural = _("doctors")

    @property
    def center(self):
        """Convenience: doctor's center is the user's center."""
        return self.user.center

    def __str__(self) -> str:
        return f"Dr. {self.user.get_full_name()}"


class Permission(models.Model):
    """Granular permission for RBAC."""

    codename = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Programmatic identifier, e.g. view_reports"),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Human-readable name, e.g. View Reports"),
    )
    category = models.CharField(
        max_length=50,
        help_text=_("Grouping category for UI, e.g. Reports"),
    )
    is_custom = models.BooleanField(
        default=False,
        help_text=_("True for superadmin-created permissions."),
    )

    class Meta:
        db_table = "core_permission"
        ordering = ["category", "codename"]
        verbose_name = _("permission")
        verbose_name_plural = _("permissions")

    def __str__(self) -> str:
        return self.codename


class Role(models.Model):
    """Tenant-scoped role with associated permissions."""

    name = models.CharField(max_length=100)
    center = models.ForeignKey(
        DiagnosticCenter,
        on_delete=models.CASCADE,
        related_name="roles",
    )
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="roles",
    )
    is_system = models.BooleanField(
        default=False,
        help_text=_("System roles cannot be deleted."),
    )

    class Meta:
        db_table = "core_role"
        ordering = ["name"]
        unique_together = [("name", "center")]
        verbose_name = _("role")
        verbose_name_plural = _("roles")

    def __str__(self) -> str:
        return f"{self.name} ({self.center.name})"


class Staff(models.Model):
    user: "User" = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_profile",
    )  # type: ignore[assignment]
    center = models.ForeignKey(
        DiagnosticCenter,
        on_delete=models.CASCADE,
        related_name="staff",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="staff_members",
    )

    class Meta:
        db_table = "core_staff"
        ordering = ["id"]
        verbose_name = _("staff")
        verbose_name_plural = _("staff")

    def __str__(self) -> str:
        return f"{self.user.get_full_name()} - {self.role.name}"

    @property
    def role_name(self) -> str:
        return self.role.name

    def has_perm(self, codename: str) -> bool:
        """Check if this staff member's role includes the given permission."""
        return self.role.permissions.filter(codename=codename).exists()

    def get_role_display(self) -> str:
        return self.role.name


class PlatformSettings(models.Model):
    """Singleton: platform-wide settings managed by SuperAdmin."""

    language = models.CharField(
        max_length=5,
        choices=LanguageChoices.choices,
        default=LanguageChoices.ENGLISH,
        help_text=_("Default language for the main LabLink landing page"),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_platform_settings"
        verbose_name = _("platform settings")
        verbose_name_plural = _("platform settings")

    def save(self, *args, **kwargs):
        self.pk = 1  # Enforce singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:
        return f"PlatformSettings (language={self.language})"
