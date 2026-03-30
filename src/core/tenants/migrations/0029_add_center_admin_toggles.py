"""
Add center-admin-level master toggles: use_sms, use_email, use_ai.

These let the center admin activate/deactivate features that the
superadmin has unlocked (can_use_*). Defaults to True so that
when a superadmin unlocks a feature, it's immediately usable.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0028_sync_center_entitlements"),
    ]

    operations = [
        migrations.AddField(
            model_name="diagnosticcenter",
            name="use_sms",
            field=models.BooleanField(
                default=True,
                help_text="Center admin: activate SMS features for this center",
            ),
        ),
        migrations.AddField(
            model_name="diagnosticcenter",
            name="use_email",
            field=models.BooleanField(
                default=True,
                help_text="Center admin: activate Email features for this center",
            ),
        ),
        migrations.AddField(
            model_name="diagnosticcenter",
            name="use_ai",
            field=models.BooleanField(
                default=True,
                help_text="Center admin: activate AI features for this center",
            ),
        ),
    ]
