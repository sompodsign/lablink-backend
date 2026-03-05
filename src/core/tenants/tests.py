import logging

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.appointments.models import Appointment
from apps.diagnostics.models import CenterTestPricing, TestOrder, TestType
from core.tenants.models import DiagnosticCenter, Doctor, Staff
from core.tenants.permissions import (
    IsCenterAdmin,
    IsCenterDoctor,
    IsCenterLabTechnician,
    IsCenterStaff,
)
from core.users.models import PatientProfile

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_center(name='Center A', domain='center-a'):
    return DiagnosticCenter.objects.create(
        name=name,
        domain=domain,
        address='123 Test St',
        contact_number='01700000001',
    )


def make_user(username, first_name='Test', last_name='User', phone=''):
    return User.objects.create_user(
        username=username,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone,
        password='testpass123',
    )


def make_staff(user, center, role=Staff.Role.RECEPTIONIST):
    return Staff.objects.create(user=user, center=center, role=role)


def make_doctor(user, *centers):
    doctor = Doctor.objects.create(user=user, specialization='General', designation='MD')
    for c in centers:
        doctor.centers.add(c)
    return doctor


def make_patient(username, center):
    user = make_user(username, 'Pat', 'ient')
    PatientProfile.objects.create(user=user, registered_at_center=center)
    return user


def make_appointment(patient, center, doctor=None):
    return Appointment.objects.create(
        patient=patient,
        center=center,
        doctor=doctor,
        date='2026-03-10',
        time='10:00',
    )


def make_test_type(name='CBC', price='500.00'):
    return TestType.objects.create(name=name, description='Blood test', base_price=price)


def jwt_auth_header(user):
    token = RefreshToken.for_user(user).access_token
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


class FakeRequest:
    """Minimal request-like object for permission testing."""

    def __init__(self, user, tenant):
        self.user = user
        self.tenant = tenant


# ---------------------------------------------------------------------------
# Permission Unit Tests
# ---------------------------------------------------------------------------

class PermissionClassTests(TestCase):
    def setUp(self):
        self.center_a = make_center('Center A', 'center-a')
        self.center_b = make_center('Center B', 'center-b')

        self.staff_user = make_user('staff_a')
        make_staff(self.staff_user, self.center_a, Staff.Role.RECEPTIONIST)

        self.admin_user = make_user('admin_a')
        make_staff(self.admin_user, self.center_a, Staff.Role.ADMIN)

        self.lab_tech_user = make_user('labtech_a')
        make_staff(self.lab_tech_user, self.center_a, Staff.Role.LAB_TECHNICIAN)

        self.doctor_user = make_user('doctor_a')
        make_doctor(self.doctor_user, self.center_a)

        self.outsider_user = make_user('outsider')

    def _req(self, user, center):
        return FakeRequest(user, center)

    def test_is_center_staff_allows_staff(self):
        req = self._req(self.staff_user, self.center_a)
        self.assertTrue(IsCenterStaff().has_permission(req, None))

    def test_is_center_staff_denies_doctor(self):
        req = self._req(self.doctor_user, self.center_a)
        self.assertFalse(IsCenterStaff().has_permission(req, None))

    def test_is_center_staff_denies_wrong_center(self):
        req = self._req(self.staff_user, self.center_b)
        self.assertFalse(IsCenterStaff().has_permission(req, None))

    def test_is_center_doctor_allows_doctor(self):
        req = self._req(self.doctor_user, self.center_a)
        self.assertTrue(IsCenterDoctor().has_permission(req, None))

    def test_is_center_doctor_denies_wrong_center(self):
        req = self._req(self.doctor_user, self.center_b)
        self.assertFalse(IsCenterDoctor().has_permission(req, None))

    def test_is_center_admin_allows_admin(self):
        req = self._req(self.admin_user, self.center_a)
        self.assertTrue(IsCenterAdmin().has_permission(req, None))

    def test_is_center_admin_denies_receptionist(self):
        req = self._req(self.staff_user, self.center_a)
        self.assertFalse(IsCenterAdmin().has_permission(req, None))

    def test_is_center_lab_technician_allows_lab_tech(self):
        req = self._req(self.lab_tech_user, self.center_a)
        self.assertTrue(IsCenterLabTechnician().has_permission(req, None))

    def test_is_center_lab_technician_denies_receptionist(self):
        req = self._req(self.staff_user, self.center_a)
        self.assertFalse(IsCenterLabTechnician().has_permission(req, None))


# ---------------------------------------------------------------------------
# Multi-Tenant Isolation Integration Tests
# ---------------------------------------------------------------------------

class TenantIsolationTests(APITestCase):
    """
    Verify that staff from Center A cannot see data from Center B.
    """

    def setUp(self):
        self.center_a = make_center('Center A', 'center-a')
        self.center_b = make_center('Center B', 'center-b')

        # Center A actors
        self.staff_a_user = make_user('staff_a')
        self.staff_a = make_staff(self.staff_a_user, self.center_a, Staff.Role.ADMIN)

        # Center B actors
        self.staff_b_user = make_user('staff_b')
        self.staff_b = make_staff(self.staff_b_user, self.center_b, Staff.Role.ADMIN)

        # Patients
        self.patient_a = make_patient('patient_a', self.center_a)
        self.patient_b = make_patient('patient_b', self.center_b)

        # Appointments
        self.appt_a = make_appointment(self.patient_a, self.center_a)
        self.appt_b = make_appointment(self.patient_b, self.center_b)

        # Test type + test orders
        self.test_type = make_test_type()
        CenterTestPricing.objects.create(
            center=self.center_a, test_type=self.test_type, price=500, is_available=True
        )
        CenterTestPricing.objects.create(
            center=self.center_b, test_type=self.test_type, price=500, is_available=True
        )

        self.order_a = TestOrder.objects.create(
            appointment=self.appt_a,
            center=self.center_a,
            test_type=self.test_type,
        )
        self.order_b = TestOrder.objects.create(
            appointment=self.appt_b,
            center=self.center_b,
            test_type=self.test_type,
        )

    def _auth(self, user, tenant):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults['SERVER_NAME'] = tenant.domain + '.localhost'

    def test_staff_a_cannot_see_center_b_test_orders(self):
        """Staff A sees only Center A's test orders."""
        self._auth(self.staff_a_user, self.center_a)
        response = self.client.get('/api/diagnostics/test-orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(self.order_a.id, ids)
        self.assertNotIn(self.order_b.id, ids)

    def test_staff_b_cannot_see_center_a_test_orders(self):
        """Staff B sees only Center B's test orders."""
        self._auth(self.staff_b_user, self.center_b)
        response = self.client.get('/api/diagnostics/test-orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertNotIn(self.order_a.id, ids)
        self.assertIn(self.order_b.id, ids)

    def test_staff_a_cannot_see_center_b_patients(self):
        """Staff A cannot see patients registered at Center B."""
        self._auth(self.staff_a_user, self.center_a)
        response = self.client.get('/api/auth/patients/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertIn(self.patient_a.id, ids)
        self.assertNotIn(self.patient_b.id, ids)


# ---------------------------------------------------------------------------
# Patient Registration Tests
# ---------------------------------------------------------------------------

class PatientRegistrationTests(APITestCase):
    def setUp(self):
        self.center = make_center()
        self.admin_user = make_user('admin_user')
        make_staff(self.admin_user, self.center, Staff.Role.ADMIN)
        self.client.credentials(**jwt_auth_header(self.admin_user))
        self.client.defaults['SERVER_NAME'] = self.center.domain + '.localhost'

    def test_staff_can_register_patient(self):
        payload = {
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '01700000099',
            'blood_group': 'A+',
        }
        response = self.client.post('/api/auth/patients/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['first_name'], 'John')
        self.assertIn('patient_profile', response.data)

    def test_patient_profile_linked_to_center(self):
        payload = {'first_name': 'Jane', 'last_name': 'Doe'}
        response = self.client.post('/api/auth/patients/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_id = response.data['id']
        profile = PatientProfile.objects.get(user_id=user_id)
        self.assertEqual(profile.registered_at_center, self.center)
