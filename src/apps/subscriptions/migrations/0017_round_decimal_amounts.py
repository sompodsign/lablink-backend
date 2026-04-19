from decimal import Decimal, ROUND_UP

from django.db import migrations


def round_credit_balances(apps, schema_editor):
    DiagnosticCenter = apps.get_model('tenants', 'DiagnosticCenter')
    for center in DiagnosticCenter.objects.filter(credit_balance__isnull=False):
        if center.credit_balance is not None:
            rounded = center.credit_balance.quantize(Decimal('1'), rounding=ROUND_UP)
            if center.credit_balance != rounded:
                center.credit_balance = rounded
                center.save(update_fields=['credit_balance'])


def round_invoice_amounts(apps, schema_editor):
    Invoice = apps.get_model('subscriptions', 'Invoice')
    for invoice in Invoice.objects.all():
        changed = False
        if invoice.credit_applied and invoice.credit_applied != invoice.credit_applied.quantize(Decimal('1'), rounding=ROUND_UP):
            invoice.credit_applied = invoice.credit_applied.quantize(Decimal('1'), rounding=ROUND_UP)
            changed = True
        if invoice.amount and invoice.amount != invoice.amount.quantize(Decimal('1'), rounding=ROUND_UP):
            invoice.amount = invoice.amount.quantize(Decimal('1'), rounding=ROUND_UP)
            changed = True
        if invoice.original_amount and invoice.original_amount != invoice.original_amount.quantize(Decimal('1'), rounding=ROUND_UP):
            invoice.original_amount = invoice.original_amount.quantize(Decimal('1'), rounding=ROUND_UP)
            changed = True
        if changed:
            invoice.save(update_fields=['amount', 'original_amount', 'credit_applied'])


class Migration(migrations.Migration):
    dependencies = [
        ('subscriptions', '0016_backfill_has_used_trial'),
        ('tenants', '0032_add_has_used_trial'),
    ]

    operations = [
        migrations.RunPython(round_credit_balances, migrations.RunPython.noop),
        migrations.RunPython(round_invoice_amounts, migrations.RunPython.noop),
    ]