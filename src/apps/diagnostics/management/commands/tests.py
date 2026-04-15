from django.core.management import CommandError, call_command
from django.test import TestCase

from apps.diagnostics.models import CenterTestPricing, ReportTemplate, TestType
from apps.diagnostics.template_fields import TEMPLATE_FIELDS
from helpers.test_factories import make_center, make_test_type


class SeedReportTemplatesCommandTests(TestCase):
    """Tests for the seed_report_templates management command."""

    def setUp(self):
        # `make_center()` clears seeded pricing for test isolation.
        # We remove templates here so the command starts from a clean state.
        self.center = make_center()
        ReportTemplate.objects.filter(center=self.center).delete()

    def test_seeds_all_centers(self):
        """Command seeds templates for all centers when no filter given."""
        call_command("seed_report_templates")
        count = ReportTemplate.objects.filter(center=self.center).count()
        self.assertGreater(count, 0)

    def test_seeds_pricing_disabled_by_default(self):
        """Seeded pricing rows start disabled until the center enables them."""
        call_command("seed_report_templates")
        pricing = CenterTestPricing.objects.filter(center=self.center)
        self.assertTrue(pricing.exists())
        self.assertFalse(pricing.filter(is_available=True).exists())

    def test_seeds_extracted_imaging_test_types(self):
        """Command seeds imaging tests extracted from the latest tariff list."""
        call_command("seed_report_templates")

        expected_names = [
            "CT Urogram",
            "USG of TVS",
            "USG of Parathyroid",
            "Endoscopy Upper GIT",
            "ECG (12CH)",
            "X-Ray KUB",
        ]
        for name in expected_names:
            with self.subTest(test_type=name):
                self.assertTrue(TestType.objects.filter(name=name).exists())

    def test_seeds_extracted_lab_test_types_from_second_board(self):
        """Command seeds additional lab tests extracted from the second tariff list."""
        call_command("seed_report_templates")

        expected_names = [
            "Hb Electrophoresis",
            "PCV (Packed Cell Volume)",
            "ADA (Adenosine Deaminase)",
            "TPHA (Treponema pallidum Hemagglutination Assay)",
            "H. pylori (ICT)",
            "Crossmatching",
        ]
        for name in expected_names:
            with self.subTest(test_type=name):
                self.assertTrue(TestType.objects.filter(name=name).exists())

    def test_skips_already_seeded_centers(self):
        """Without --force, existing templates are not overwritten."""
        call_command("seed_report_templates")
        initial_count = ReportTemplate.objects.filter(center=self.center).count()

        # Run again — should skip all
        call_command("seed_report_templates")
        final_count = ReportTemplate.objects.filter(center=self.center).count()
        self.assertEqual(initial_count, final_count)

    def test_force_flag_overwrites(self):
        """--force re-seeds templates even if they already exist."""
        call_command("seed_report_templates")

        # Corrupt a template's fields
        template = ReportTemplate.objects.filter(center=self.center).first()
        _original_fields = list(template.fields)
        template.fields = [{"name": "corrupted"}]
        template.save()

        # Force re-seed
        call_command("seed_report_templates", force=True)
        template.refresh_from_db()
        self.assertNotEqual(template.fields, [{"name": "corrupted"}])

    def test_filter_by_domain(self):
        """--domain seeds only the matching center."""
        center_b = make_center("Center B", "center-b")
        ReportTemplate.objects.filter(center=center_b).delete()

        call_command("seed_report_templates", domain=self.center.domain)

        a_count = ReportTemplate.objects.filter(center=self.center).count()
        b_count = ReportTemplate.objects.filter(center=center_b).count()
        self.assertGreater(a_count, 0)
        self.assertEqual(b_count, 0)

    def test_filter_by_center_id(self):
        """--center-id seeds only the matching center."""
        call_command("seed_report_templates", center_id=self.center.id)
        count = ReportTemplate.objects.filter(center=self.center).count()
        self.assertGreater(count, 0)

    def test_invalid_domain_raises_error(self):
        """Non-existent domain raises CommandError."""
        with self.assertRaises(CommandError):
            call_command("seed_report_templates", domain="nonexistent")

    def test_invalid_center_id_raises_error(self):
        """Non-existent center ID raises CommandError."""
        with self.assertRaises(CommandError):
            call_command("seed_report_templates", center_id=99999)

    def test_both_filters_raises_error(self):
        """Specifying both --domain and --center-id raises CommandError."""
        with self.assertRaises(CommandError):
            call_command(
                "seed_report_templates",
                domain=self.center.domain,
                center_id=self.center.id,
            )

    def test_only_matching_test_types_seeded(self):
        """Only TestTypes present in TEMPLATE_FIELDS get templates."""
        custom_tt = make_test_type("Totally Custom Test", "100.00")
        call_command("seed_report_templates")
        has_custom = ReportTemplate.objects.filter(
            center=self.center,
            test_type=custom_tt,
        ).exists()
        self.assertFalse(has_custom)


class CreateReportTemplatesSignalTests(TestCase):
    """Test that the post_save signal auto-creates templates for new centers."""

    def test_new_center_gets_templates_and_disabled_pricing(self):
        """Creating a new center auto-creates templates and disabled pricing."""
        # Create test types whose names match entries in TEMPLATE_FIELDS
        sample_names = list(TEMPLATE_FIELDS.keys())[:3]
        for name in sample_names:
            TestType.objects.get_or_create(
                name=name,
                defaults={"base_price": "100.00"},
            )

        # Count how many TestType rows match the seed data
        matching = TestType.objects.filter(
            name__in=TEMPLATE_FIELDS.keys(),
        ).count()
        self.assertGreaterEqual(matching, 3)

        # Now create a center — the signal should fire
        from core.tenants.models import DiagnosticCenter

        center = DiagnosticCenter.objects.create(
            name="Signal Test Center",
            domain="signal-test",
        )

        templates = ReportTemplate.objects.filter(center=center).count()
        self.assertEqual(templates, matching)
        pricing = CenterTestPricing.objects.filter(center=center)
        self.assertEqual(pricing.count(), matching)
        self.assertFalse(pricing.filter(is_available=True).exists())
