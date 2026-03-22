"""Seed report templates and pricing for one, many, or all diagnostic centers.

Usage:
    # All centers (skip those already seeded):
    python manage.py seed_report_templates

    # Specific center by domain:
    python manage.py seed_report_templates --domain alpha

    # Specific center by ID:
    python manage.py seed_report_templates --center-id 3

    # Force re-seed (overwrite existing templates):
    python manage.py seed_report_templates --force
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.diagnostics.models import CenterTestPricing, ReportTemplate, TestType
from apps.diagnostics.template_fields import TEMPLATE_FIELDS
from core.tenants.models import DiagnosticCenter

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Seed default report templates and pricing for diagnostic centers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            type=str,
            help="Seed templates for a single center identified by its domain.",
        )
        parser.add_argument(
            "--center-id",
            type=int,
            help="Seed templates for a single center identified by its PK.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Overwrite existing templates (default: skip centers that already have templates).",
        )

    def handle(self, *args, **options):
        centers = self._resolve_centers(options)
        force = options["force"]

        total_tmpl_created = 0
        total_tmpl_skipped = 0
        total_price_created = 0
        total_price_skipped = 0

        test_types = {tt.name: tt for tt in TestType.objects.all()}

        for center in centers:
            t_created, t_skipped = self._seed_templates(
                center,
                test_types,
                force,
            )
            p_created, p_skipped = self._seed_pricing(center, test_types)
            total_tmpl_created += t_created
            total_tmpl_skipped += t_skipped
            total_price_created += p_created
            total_price_skipped += p_skipped

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — templates: {total_tmpl_created} created, "
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

    # ── Templates ──────────────────────────────────────────────
    def _seed_templates(self, center, test_types, force):
        created = 0
        skipped = 0

        existing = set(
            ReportTemplate.objects.filter(center=center).values_list(
                "test_type_id",
                flat=True,
            )
        )

        templates_to_create = []
        templates_to_update = []

        for test_name, fields in TEMPLATE_FIELDS.items():
            tt = test_types.get(test_name)
            if tt is None:
                continue

            if tt.id in existing:
                if force:
                    templates_to_update.append((tt, fields))
                else:
                    skipped += 1
                continue

            templates_to_create.append(
                ReportTemplate(center=center, test_type=tt, fields=fields)
            )

        if templates_to_create:
            ReportTemplate.objects.bulk_create(
                templates_to_create,
                ignore_conflicts=True,
            )
            created = len(templates_to_create)

        if templates_to_update:
            for tt, fields in templates_to_update:
                ReportTemplate.objects.filter(
                    center=center,
                    test_type=tt,
                ).update(fields=fields)
                created += 1

        self.stdout.write(
            f"  {center.name}: templates — {created} created, {skipped} skipped"
        )
        return created, skipped

    # ── Pricing ────────────────────────────────────────────────
    def _seed_pricing(self, center, test_types):
        existing = set(
            CenterTestPricing.objects.filter(center=center).values_list(
                "test_type_id",
                flat=True,
            )
        )

        to_create = []
        for tt in test_types.values():
            if tt.id in existing:
                continue
            to_create.append(
                CenterTestPricing(
                    center=center,
                    test_type=tt,
                    price=tt.base_price,
                    is_available=True,
                )
            )

        if to_create:
            CenterTestPricing.objects.bulk_create(
                to_create,
                ignore_conflicts=True,
            )

        created = len(to_create)
        skipped = len(existing)
        self.stdout.write(
            f"  {center.name}: pricing  — {created} created, {skipped} skipped"
        )
        return created, skipped
