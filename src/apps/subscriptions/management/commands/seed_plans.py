import logging

from django.core.management.base import BaseCommand

from apps.subscriptions.models import SubscriptionPlan

logger = logging.getLogger(__name__)

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


class Command(BaseCommand):
    help = "Seed default subscription plans"

    def handle(self, *args, **options):
        for plan_data in PLANS:
            plan, created = SubscriptionPlan.objects.update_or_create(
                slug=plan_data["slug"],
                defaults=plan_data,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(f"{action} plan: {plan.name} (৳{plan.price}/mo)")
            )

        self.stdout.write(self.style.SUCCESS("Done seeding subscription plans."))
