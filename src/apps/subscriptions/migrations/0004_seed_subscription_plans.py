"""Seed the 4-tier subscription plans via data migration.

Ensures plans exist in production after `manage.py migrate`
without needing to manually run `seed_plans`.
"""

from django.db import migrations

PLANS = [
    {
        "name": "Free Trial",
        "slug": "trial",
        "price": 0,
        "trial_days": 30,
        "max_staff": 30,
        "max_reports": 3000,
        "features": [
            "Up to 30 staff accounts",
            "Up to 3,000 reports/month",
            "Online appointment booking",
            "Advanced analytics",
            "Custom branding & domain",
            "Full feature access",
            "30-day free trial",
        ],
        "display_order": 0,
    },
    {
        "name": "Basic",
        "slug": "basic",
        "price": 999,
        "trial_days": 14,
        "max_staff": 5,
        "max_reports": 500,
        "features": [
            "Up to 5 staff accounts",
            "Up to 500 reports/month",
            "Online appointment booking",
            "Basic analytics",
            "Email support",
        ],
        "display_order": 1,
    },
    {
        "name": "Starter",
        "slug": "starter",
        "price": 2499,
        "trial_days": 14,
        "max_staff": 15,
        "max_reports": 1500,
        "features": [
            "Up to 15 staff accounts",
            "Up to 1,500 reports/month",
            "Online appointment booking",
            "Advanced analytics",
            "Custom branding & domain",
            "Email support",
        ],
        "display_order": 2,
    },
    {
        "name": "Professional",
        "slug": "professional",
        "price": 4999,
        "trial_days": 14,
        "max_staff": 30,
        "max_reports": 3000,
        "features": [
            "Up to 30 staff accounts",
            "Up to 3,000 reports/month",
            "Everything in Starter",
            "Advanced analytics & reports",
            "Custom branding & domain",
            "Priority support",
        ],
        "display_order": 3,
    },
]


def seed_plans(apps, _schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")
    for plan_data in PLANS:
        SubscriptionPlan.objects.update_or_create(
            slug=plan_data["slug"],
            defaults=plan_data,
        )


def unseed_plans(apps, _schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")
    slugs = [p["slug"] for p in PLANS]
    SubscriptionPlan.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0003_add_max_reports_to_plan"),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed_plans),
    ]
