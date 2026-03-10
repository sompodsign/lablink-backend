"""
Scope ReportTemplate to tenant — Part 2: Data migration.

Populate center for existing ReportTemplate rows.
"""

from django.db import migrations


def populate_center(apps, schema_editor):
    """Clone templates to every center that offers the test type."""
    ReportTemplate = apps.get_model('diagnostics', 'ReportTemplate')
    CenterTestPricing = apps.get_model('diagnostics', 'CenterTestPricing')
    DiagnosticCenter = apps.get_model('tenants', 'DiagnosticCenter')

    all_centers = list(DiagnosticCenter.objects.all())
    if not all_centers:
        return

    for template in ReportTemplate.objects.filter(center__isnull=True):
        pricing_center_ids = list(
            CenterTestPricing.objects.filter(
                test_type=template.test_type,
            ).values_list('center_id', flat=True)
        )

        if pricing_center_ids:
            template.center_id = pricing_center_ids[0]
            template.save(update_fields=['center_id'])

            for center_id in pricing_center_ids[1:]:
                ReportTemplate.objects.get_or_create(
                    center_id=center_id,
                    test_type=template.test_type,
                    defaults={'fields': template.fields},
                )
        else:
            template.center_id = all_centers[0].id
            template.save(update_fields=['center_id'])


def reverse_populate(apps, schema_editor):
    """Keep only one template per test_type (remove duplicates)."""
    ReportTemplate = apps.get_model('diagnostics', 'ReportTemplate')
    seen = set()
    for template in ReportTemplate.objects.order_by('id'):
        if template.test_type_id in seen:
            template.delete()
        else:
            template.center_id = None
            template.save(update_fields=['center_id'])
            seen.add(template.test_type_id)


class Migration(migrations.Migration):

    dependencies = [
        ('diagnostics', '0011_scope_report_template_to_tenant'),
    ]

    operations = [
        migrations.RunPython(populate_center, reverse_populate),
    ]
