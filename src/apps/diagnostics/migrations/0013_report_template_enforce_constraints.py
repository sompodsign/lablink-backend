"""
Scope ReportTemplate to tenant — Part 3: Enforce constraints.

Delete any orphaned rows where center is still null (e.g. from seed migration
running on an empty DB with no centers), then make center non-nullable and
add unique_together.
"""

import django.db.models.deletion
from django.db import migrations, models


def remove_null_center_rows(apps, schema_editor):
    """Remove templates that couldn't be assigned a center."""
    ReportTemplate = apps.get_model('diagnostics', 'ReportTemplate')
    ReportTemplate.objects.filter(center__isnull=True).delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('diagnostics', '0012_report_template_nonnull_center'),
    ]

    operations = [
        # Clean up any rows where center is still null
        migrations.RunPython(remove_null_center_rows, noop),

        # Now safe to make center non-nullable
        migrations.AlterField(
            model_name='reporttemplate',
            name='center',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='report_templates',
                to='tenants.diagnosticcenter',
            ),
        ),

        migrations.AlterUniqueTogether(
            name='reporttemplate',
            unique_together={('center', 'test_type')},
        ),
    ]
