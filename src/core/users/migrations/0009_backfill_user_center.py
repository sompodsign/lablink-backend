"""Data migration: backfill User.center from Staff, Doctor, and PatientProfile."""

from django.db import migrations


def backfill_user_center(apps, _schema_editor):
    """Populate User.center from existing profile relationships."""
    User = apps.get_model('users', 'User')
    Staff = apps.get_model('tenants', 'Staff')
    PatientProfile = apps.get_model('users', 'PatientProfile')

    # Staff → center
    for staff in Staff.objects.select_related('user', 'center').all():
        if staff.user.center_id is None:
            staff.user.center = staff.center
            staff.user.save(update_fields=['center_id'])

    # Doctor → first center from the old M2M (through table still exists)
    # We read directly from the M2M through table before it's dropped
    Doctor = apps.get_model('tenants', 'Doctor')
    DoctorCenters = Doctor.centers.through  # noqa: N806
    for dc in DoctorCenters.objects.select_related('doctor__user').all():
        user = dc.doctor.user
        if user.center_id is None:
            user.center_id = dc.diagnosticcenter_id
            user.save(update_fields=['center_id'])

    # Patient → registered_at_center
    for profile in PatientProfile.objects.select_related(
        'user', 'registered_at_center',
    ).filter(registered_at_center__isnull=False):
        if profile.user.center_id is None:
            profile.user.center = profile.registered_at_center
            profile.user.save(update_fields=['center_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_user_center_fk_and_doctor_m2m_removal'),
    ]

    operations = [
        migrations.RunPython(
            backfill_user_center,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
