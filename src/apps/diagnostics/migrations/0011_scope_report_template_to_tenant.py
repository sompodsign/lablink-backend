"""
Scope ReportTemplate to tenant — Part 1: Schema changes.

Add nullable center FK and change test_type from OneToOne to FK.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("diagnostics", "0010_gender_specific_ref_ranges"),
        ("tenants", "0006_add_phone_number_and_patient_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="reporttemplate",
            name="center",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="report_templates",
                to="tenants.diagnosticcenter",
            ),
        ),
        migrations.AlterField(
            model_name="reporttemplate",
            name="test_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="report_templates",
                to="diagnostics.testtype",
            ),
        ),
    ]
