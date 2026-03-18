import logging

from django.core.management.base import BaseCommand

from apps.subscriptions.models import SubscriptionPlan

logger = logging.getLogger(__name__)

PLANS = [
    {
        'name': 'Free Trial',
        'slug': 'trial',
        'price': 0,
        'trial_days': 14,
        'max_staff': -1,
        'features': [
            'Unlimited staff accounts',
            'Unlimited reports',
            'Online appointment booking',
            'Advanced analytics',
            'Custom branding & domain',
            'Full feature access',
        ],
        'display_order': 0,
    },
    {
        'name': 'Starter',
        'slug': 'starter',
        'price': 2499,
        'trial_days': 14,
        'max_staff': 15,
        'features': [
            'Up to 15 staff accounts',
            'Unlimited reports',
            'Online appointment booking',
            'Advanced analytics',
            'Custom branding & domain',
            'Email support',
        ],
        'display_order': 1,
    },
    {
        'name': 'Professional',
        'slug': 'professional',
        'price': 4999,
        'trial_days': 14,
        'max_staff': -1,
        'features': [
            'Unlimited staff accounts',
            'Unlimited reports',
            'Everything in Starter',
            'Advanced analytics & reports',
            'Custom branding & domain',
            'Priority support',
        ],
        'display_order': 2,
    },
]


class Command(BaseCommand):
    help = 'Seed default subscription plans'

    def handle(self, *args, **options):
        for plan_data in PLANS:
            plan, created = SubscriptionPlan.objects.update_or_create(
                slug=plan_data['slug'],
                defaults=plan_data,
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(
                self.style.SUCCESS(f'{action} plan: {plan.name} (৳{plan.price}/mo)')
            )

        self.stdout.write(self.style.SUCCESS('Done seeding subscription plans.'))
