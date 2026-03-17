from django.contrib.auth.models import Group
from django.db import migrations


def add_lab_tech_group(apps, schema_editor):
    Group.objects.get_or_create(name="LABLINK | LAB_TECHNICIAN")


def remove_lab_tech_group(apps, schema_editor):
    Group.objects.filter(name="LABLINK | LAB_TECHNICIAN").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_create_lablink_groups"),
    ]

    operations = [
        migrations.RunPython(add_lab_tech_group, remove_lab_tech_group),
    ]
