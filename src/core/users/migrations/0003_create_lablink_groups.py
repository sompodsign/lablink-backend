from django.contrib.auth.models import Group
from django.db import migrations

GROUPS = [
    "LABLINK | BASIC",
    "LABLINK | STAFF",
    "LABLINK | ADMIN",
    "LABLINK | DOCTOR",
]


def create_groups(apps, schema_editor):
    for name in GROUPS:
        Group.objects.get_or_create(name=name)


def remove_groups(apps, schema_editor):
    Group.objects.filter(name__in=GROUPS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_add_phone_number_and_patient_profile"),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]
