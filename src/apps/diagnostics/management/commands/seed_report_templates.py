"""Seed report templates for one, many, or all diagnostic centers.

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

from apps.diagnostics.models import ReportTemplate, TestType
from apps.diagnostics.template_fields import TEMPLATE_FIELDS
from core.tenants.models import DiagnosticCenter

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Seed default report templates for diagnostic centers."

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

        total_created = 0
        total_skipped = 0

        test_types = {tt.name: tt for tt in TestType.objects.all()}

        for center in centers:
            created, skipped = self._seed_center(center, test_types, force)
            total_created += created
            total_skipped += skipped

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — created {total_created} templates, "
                f"skipped {total_skipped} (already existed)."
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

    def _seed_center(self, center, test_types, force):
        created = 0
        skipped = 0

        existing = set(
            ReportTemplate.objects.filter(center=center).values_list(
                "test_type_id", flat=True
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

        logger.info(
            'Center "%s": created=%d, skipped=%d',
            center.name,
            created,
            skipped,
        )
        self.stdout.write(f"  {center.name}: {created} created, {skipped} skipped")
        return created, skipped
