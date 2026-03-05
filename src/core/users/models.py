from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True)


class PatientProfile(models.Model):
    class BloodGroup(models.TextChoices):
        A_POS = 'A+', _('A+')
        A_NEG = 'A-', _('A-')
        B_POS = 'B+', _('B+')
        B_NEG = 'B-', _('B-')
        AB_POS = 'AB+', _('AB+')
        AB_NEG = 'AB-', _('AB-')
        O_POS = 'O+', _('O+')
        O_NEG = 'O-', _('O-')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_profile',
    )
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    blood_group = models.CharField(
        max_length=3,
        choices=BloodGroup.choices,
        blank=True,
    )
    address = models.TextField(blank=True)
    medical_history = models.TextField(
        blank=True,
        help_text=_('Free-text medical history notes'),
    )
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    registered_at_center = models.ForeignKey(
        'tenants.DiagnosticCenter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_patients',
        help_text=_('The center where this patient was first registered'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_patient_profile'
        verbose_name = _('patient profile')
        verbose_name_plural = _('patient profiles')

    def __str__(self) -> str:
        return f'Patient: {self.user.get_full_name()}'
