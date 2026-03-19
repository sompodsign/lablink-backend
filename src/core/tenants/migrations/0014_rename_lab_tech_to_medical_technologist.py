"""Data migration: rename 'Lab Technician' → 'Medical Technologist'."""

from django.db import migrations


def forwards(apps, schema_editor):
    Role = apps.get_model('tenants', 'Role')
    Role.objects.filter(name='Lab Technician').update(name='Medical Technologist')

    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='LABLINK | LAB_TECHNICIAN').update(
        name='LABLINK | MEDICAL_TECHNOLOGIST',
    )


def backwards(apps, schema_editor):
    Role = apps.get_model('tenants', 'Role')
    Role.objects.filter(name='Medical Technologist').update(name='Lab Technician')

    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='LABLINK | MEDICAL_TECHNOLOGIST').update(
        name='LABLINK | LAB_TECHNICIAN',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0013_diagnosticcenter_allow_online_appointments'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
