from django.contrib.auth.models import Group
from django.db import migrations


def add_receptionist_group(apps, schema_editor):
    Group.objects.get_or_create(name='LABLINK | RECEPTIONIST')


def remove_receptionist_group(apps, schema_editor):
    Group.objects.filter(name='LABLINK | RECEPTIONIST').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_add_gender_to_patient_profile'),
    ]

    operations = [
        migrations.RunPython(add_receptionist_group, remove_receptionist_group),
    ]
