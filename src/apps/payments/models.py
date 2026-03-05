from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.appointments.models import Appointment


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = 'CASH', _('Cash')
        CARD = 'CARD', _('Card')
        MOBILE_BANKING = 'MOBILE_BANKING', _('Mobile Banking')
        ONLINE = 'ONLINE', _('Online Gateway')

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    test_order = models.ForeignKey(
        'diagnostics.TestOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        help_text=_('Optional: link payment to a specific test order'),
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    method = models.CharField(max_length=50, choices=Method.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'apps_payment'
        verbose_name = _('payment')
        verbose_name_plural = _('payments')

    def __str__(self) -> str:
        return f'{self.appointment} - {self.amount} - {self.status}'
