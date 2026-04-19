from django.db import migrations

PLAN_AI_CREDITS = {
    'trial': 100,
    'basic': 0,
    'starter': 0,
    'professional': 500,
    'enterprise': 5000,
}

ENTERPRISE_DEFAULTS = {
    'name': 'Enterprise',
    'price': 9999,
    'trial_days': 14,
    'max_staff': -1,
    'max_reports': -1,
    'monthly_ai_credits': 5000,
    'features': [
        'Unlimited staff accounts',
        'Unlimited reports/month',
        'Everything in Professional',
        'Custom branding & domain',
        'Dedicated support',
        'API access',
        '5,000 AI credits/month',
    ],
    'is_active': True,
    'display_order': 4,
}


def backfill_missing_ai_plan_data(apps, _schema_editor):
    SubscriptionPlan = apps.get_model('subscriptions', 'SubscriptionPlan')
    Subscription = apps.get_model('subscriptions', 'Subscription')

    SubscriptionPlan.objects.update_or_create(
        slug='enterprise',
        defaults=ENTERPRISE_DEFAULTS,
    )

    for slug, monthly_ai_credits in PLAN_AI_CREDITS.items():
        SubscriptionPlan.objects.filter(slug=slug).update(
            monthly_ai_credits=monthly_ai_credits,
        )

    credited_plan_slugs = [
        slug for slug, credits in PLAN_AI_CREDITS.items() if credits > 0
    ]

    for subscription in Subscription.objects.select_related('plan').filter(
        plan__slug__in=credited_plan_slugs,
        available_ai_credits=0,
    ):
        monthly_ai_credits = PLAN_AI_CREDITS.get(subscription.plan.slug, 0)
        if monthly_ai_credits > 0:
            subscription.available_ai_credits = monthly_ai_credits
            subscription.save(update_fields=['available_ai_credits'])


class Migration(migrations.Migration):
    dependencies = [
        ('subscriptions', '0012_invoice_payment_application_snapshot'),
    ]

    operations = [
        migrations.RunPython(
            backfill_missing_ai_plan_data,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
