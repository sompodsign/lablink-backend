from django.db import migrations


def backfill_has_used_trial(apps, schema_editor):
    DiagnosticCenter = apps.get_model('tenants', 'DiagnosticCenter')
    Subscription = apps.get_model('subscriptions', 'Subscription')
    
    centers_with_subs = Subscription.objects.values_list('center_id', flat=True).distinct()
    DiagnosticCenter.objects.filter(
        id__in=centers_with_subs,
        has_used_trial=False,
    ).update(has_used_trial=True)


class Migration(migrations.Migration):
    dependencies = [
        ('subscriptions', '0015_add_invoice_original_amount'),
        ('tenants', '0032_add_has_used_trial'),
    ]

    operations = [
        migrations.RunPython(backfill_has_used_trial, migrations.RunPython.noop),
    ]