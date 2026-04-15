"""Seed diagnostics catalog data for one, many, or all diagnostic centers.

Usage:
    # All centers (create missing global tests, pricing, and templates):
    python manage.py seed_report_templates

    # Specific center by domain:
    python manage.py seed_report_templates --domain alpha

    # Specific center by ID:
    python manage.py seed_report_templates --center-id 3

    # Force re-seed (overwrite existing templates):
    python manage.py seed_report_templates --force
"""

from django.core.management.base import BaseCommand, CommandError

from apps.diagnostics.services.seeding import seed_center_defaults, seed_test_types
from core.tenants.models import DiagnosticCenter


class Command(BaseCommand):
    help = (
        "Seed global diagnostic test types plus center pricing and report "
        "templates. Newly seeded pricing rows start disabled."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            type=str,
            help="Seed diagnostics defaults for a single center by domain.",
        )
        parser.add_argument(
            "--center-id",
            type=int,
            help="Seed diagnostics defaults for a single center by primary key.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help=(
                "Overwrite existing templates. Pricing rows remain create-missing only."
            ),
        )

    def handle(self, *args, **options):
        centers = self._resolve_centers(options)
        force = options["force"]
        test_type_summary = seed_test_types()
        test_types = test_type_summary["test_types"]

        total_tmpl_created = 0
        total_tmpl_updated = 0
        total_tmpl_skipped = 0
        total_price_created = 0
        total_price_skipped = 0

        for center in centers:
            center_summary = seed_center_defaults(
                center,
                test_types=test_types,
                force_templates=force,
                default_is_available=False,
            )
            template_summary = center_summary["templates"]
            pricing_summary = center_summary["pricing"]
            total_tmpl_created += template_summary["created"]
            total_tmpl_updated += template_summary["updated"]
            total_tmpl_skipped += template_summary["skipped"]
            total_price_created += pricing_summary["created"]
            total_price_skipped += pricing_summary["skipped"]
            self.stdout.write(
                f"  {center.name}: templates — "
                f"{template_summary['created']} created, "
                f"{template_summary['updated']} updated, "
                f"{template_summary['skipped']} skipped"
            )
            self.stdout.write(
                f"  {center.name}: pricing  — "
                f"{pricing_summary['created']} created, "
                f"{pricing_summary['skipped']} skipped"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — test types: {test_type_summary['created']} created, "
                f"{test_type_summary['skipped']} skipped | "
                f"templates: {total_tmpl_created} created, "
                f"{total_tmpl_updated} updated, "
                f"{total_tmpl_skipped} skipped | "
                f"pricing: {total_price_created} created, "
                f"{total_price_skipped} skipped."
            )
        )

    # ─────────────────────────────────────────────────────────────
    def _resolve_centers(self, options):
        domain = options.get("domain")
        center_id = options.get("center_id")

        if domain and center_id:
            raise CommandError("Specify --domain or --center-id, not both.")

        if domain:
            try:
                return [DiagnosticCenter.objects.get(domain=domain)]
            except DiagnosticCenter.DoesNotExist:
                raise CommandError(f'No center found with domain "{domain}".') from None

        if center_id:
            try:
                return [DiagnosticCenter.objects.get(pk=center_id)]
            except DiagnosticCenter.DoesNotExist:
                raise CommandError(f"No center found with ID {center_id}.") from None

        return DiagnosticCenter.objects.all()
