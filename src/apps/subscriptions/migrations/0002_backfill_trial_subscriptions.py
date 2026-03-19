"""Backfill trial subscriptions for centers that have none."""

from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def backfill_trial_subscriptions(apps, schema_editor):
    DiagnosticCenter = apps.get_model('tenants', 'DiagnosticCenter')
    Subscription = apps.get_model('subscriptions', 'Subscription')
    SubscriptionPlan = apps.get_model('subscriptions', 'SubscriptionPlan')

    trial_plan = SubscriptionPlan.objects.filter(slug='trial').first()
    if not trial_plan:
        return

    # Centers without a subscription
    centers_without_sub = DiagnosticCenter.objects.exclude(
        id__in=Subscription.objects.values_list('center_id', flat=True),
    )

    now = timezone.now()
    subs_to_create = []
    for center in centers_without_sub:
        subs_to_create.append(
            Subscription(
                center=center,
                plan=trial_plan,
                status='TRIAL',
                trial_start=now,
                trial_end=now + timedelta(days=trial_plan.trial_days),
                billing_date=(now + timedelta(days=trial_plan.trial_days)).date(),
            )
        )

    if subs_to_create:
        Subscription.objects.bulk_create(subs_to_create)


class Migration(migrations.Migration):
    dependencies = [
        ('subscriptions', '0001_initial'),
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            backfill_trial_subscriptions,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
