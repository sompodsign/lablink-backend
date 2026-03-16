"""Tests for superadmin dashboard views and deactivated-center login block."""

import logging

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from core.tenants.middleware import TenantMiddleware
from helpers.test_factories import (
    FakeRequest,
    jwt_auth_header,
    make_appointment,
    make_center,
    make_doctor,
    make_patient,
    make_staff,
    make_test_order,
    make_test_type,
    make_user,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Superadmin Dashboard View Tests
# ---------------------------------------------------------------------------


class SuperadminDashboardViewTests(APITestCase):
    """Tests for GET /api/tenants/superadmin/dashboard/."""

    def setUp(self):
        self.center_a = make_center('Center A', 'center-a')
        self.center_b = make_center('Center B', 'center-b')
        self.superuser = make_user('sa_dash', is_superuser=True)

        # Populate data
        self.staff_user = make_user('s_dash')
        make_staff(self.staff_user, self.center_a)
        self.doc_user = make_user('d_dash')
        make_doctor(self.doc_user, self.center_a)
        self.patient = make_patient('p_dash', self.center_a)

    def _auth_super(self):
        self.client.credentials(**jwt_auth_header(self.superuser))

    def _auth_staff(self):
        self.client.credentials(**jwt_auth_header(self.staff_user))
        self.client.defaults['SERVER_NAME'] = 'center-a.localhost'

    def test_superadmin_gets_stats(self):
        self._auth_super()
        response = self.client.get('/api/tenants/superadmin/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_centers', response.data)
        self.assertIn('total_users', response.data)
        self.assertIn('total_patients', response.data)
        self.assertIn('total_staff', response.data)
        self.assertIn('total_doctors', response.data)
        self.assertEqual(response.data['total_centers'], 2)

    def test_regular_user_denied(self):
        self._auth_staff()
        response = self.client.get('/api/tenants/superadmin/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_denied(self):
        response = self.client.get('/api/tenants/superadmin/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Superadmin Center Views Tests
# ---------------------------------------------------------------------------


class SuperadminCenterViewTests(APITestCase):
    """Tests for /api/tenants/superadmin/centers/ endpoints."""

    def setUp(self):
        self.center = make_center('Test Center', 'test-center')
        self.superuser = make_user('sa_center', is_superuser=True)
        self.regular = make_user('reg_center')

    def _auth(self):
        self.client.credentials(**jwt_auth_header(self.superuser))

    def test_list_centers(self):
        self._auth()
        response = self.client.get('/api/tenants/superadmin/centers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)
        names = [c['name'] for c in response.data]
        self.assertIn('Test Center', names)

    def test_list_centers_includes_counts(self):
        user = make_user('cnt_staff')
        make_staff(user, self.center)
        self._auth()
        response = self.client.get('/api/tenants/superadmin/centers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        center_data = next(c for c in response.data if c['name'] == 'Test Center')
        self.assertIn('staff_count', center_data)
        self.assertGreaterEqual(center_data['staff_count'], 1)

    def test_get_center_detail(self):
        self._auth()
        response = self.client.get(
            f'/api/tenants/superadmin/centers/{self.center.id}/',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Center')

    def test_get_center_detail_404(self):
        self._auth()
        response = self.client.get('/api/tenants/superadmin/centers/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_center(self):
        self._auth()
        response = self.client.patch(
            f'/api/tenants/superadmin/centers/{self.center.id}/',
            {'name': 'Updated Center'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.center.refresh_from_db()
        self.assertEqual(self.center.name, 'Updated Center')

    def test_toggle_center_deactivates(self):
        self._auth()
        self.assertTrue(self.center.is_active)
        response = self.client.post(
            f'/api/tenants/superadmin/centers/{self.center.id}/toggle-active/',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_active'])
        self.center.refresh_from_db()
        self.assertFalse(self.center.is_active)

    def test_toggle_center_activates(self):
        self.center.is_active = False
        self.center.save()
        self._auth()
        response = self.client.post(
            f'/api/tenants/superadmin/centers/{self.center.id}/toggle-active/',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_active'])

    def test_toggle_center_not_found(self):
        self._auth()
        response = self.client.post(
            '/api/tenants/superadmin/centers/99999/toggle-active/',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_superadmin_denied(self):
        self.client.credentials(**jwt_auth_header(self.regular))
        response = self.client.get('/api/tenants/superadmin/centers/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Superadmin User Views Tests
# ---------------------------------------------------------------------------


class SuperadminUserViewTests(APITestCase):
    """Tests for /api/tenants/superadmin/users/ endpoints."""

    def setUp(self):
        self.center = make_center('User Center', 'user-center')
        self.superuser = make_user('sa_user_v', is_superuser=True)

        self.staff_user = make_user('u_staff', 'Staff', 'User')
        make_staff(self.staff_user, self.center, 'Receptionist')

        self.doc_user = make_user('u_doc', 'Doc', 'User')
        make_doctor(self.doc_user, self.center)

        self.patient = make_patient('u_patient', self.center)

    def _auth(self):
        self.client.credentials(**jwt_auth_header(self.superuser))

    def test_list_all_users(self):
        self._auth()
        response = self.client.get('/api/tenants/superadmin/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_filter_by_type_staff(self):
        self._auth()
        response = self.client.get('/api/tenants/superadmin/users/?type=staff')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for u in response.data:
            self.assertEqual(u['user_type'], 'staff')

    def test_filter_by_type_doctor(self):
        self._auth()
        response = self.client.get('/api/tenants/superadmin/users/?type=doctor')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for u in response.data:
            self.assertEqual(u['user_type'], 'doctor')

    def test_filter_by_type_patient(self):
        self._auth()
        response = self.client.get(
            '/api/tenants/superadmin/users/?type=patient',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for u in response.data:
            self.assertEqual(u['user_type'], 'patient')

    def test_filter_by_center(self):
        self._auth()
        response = self.client.get(
            f'/api/tenants/superadmin/users/?center={self.center.id}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_search_by_name(self):
        self._auth()
        response = self.client.get(
            '/api/tenants/superadmin/users/?search=Staff',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        found = [u for u in response.data if u['first_name'] == 'Staff']
        self.assertGreater(len(found), 0)

    def test_get_user_detail(self):
        self._auth()
        response = self.client.get(
            f'/api/tenants/superadmin/users/{self.staff_user.id}/',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'u_staff')

    def test_get_user_detail_404(self):
        self._auth()
        response = self.client.get('/api/tenants/superadmin/users/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_user(self):
        self._auth()
        response = self.client.patch(
            f'/api/tenants/superadmin/users/{self.staff_user.id}/',
            {'is_active': False},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.staff_user.refresh_from_db()
        self.assertFalse(self.staff_user.is_active)

    def test_delete_user(self):
        self._auth()
        target = make_user('deletable_user')
        response = self.client.delete(
            f'/api/tenants/superadmin/users/{target.id}/',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(id=target.id).exists())

    def test_cannot_delete_superadmin(self):
        self._auth()
        response = self.client.delete(
            f'/api/tenants/superadmin/users/{self.superuser.id}/',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Superadmin Entity List Tests (Patients, Staff, Doctors)
# ---------------------------------------------------------------------------


class SuperadminEntityListTests(APITestCase):
    """Tests for /api/tenants/superadmin/patients|staff|doctors/."""

    def setUp(self):
        self.center_a = make_center('Entity A', 'entity-a')
        self.center_b = make_center('Entity B', 'entity-b')
        self.superuser = make_user('sa_entity', is_superuser=True)

        self.staff_user = make_user('e_staff')
        make_staff(self.staff_user, self.center_a, 'Admin')

        self.doc_user = make_user('e_doc')
        make_doctor(self.doc_user, self.center_a)

        self.patient_a = make_patient('e_pat_a', self.center_a)
        self.patient_b = make_patient('e_pat_b', self.center_b)

    def _auth(self):
        self.client.credentials(**jwt_auth_header(self.superuser))

    def test_list_all_patients(self):
        self._auth()
        response = self.client.get('/api/tenants/superadmin/patients/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_filter_patients_by_center(self):
        self._auth()
        response = self.client.get(
            f'/api/tenants/superadmin/patients/?center={self.center_a.id}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        for p in response.data:
            self.assertEqual(p['center_name'], 'Entity A')

    def test_list_all_staff(self):
        self._auth()
        response = self.client.get('/api/tenants/superadmin/staff/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_filter_staff_by_center(self):
        self._auth()
        response = self.client.get(
            f'/api/tenants/superadmin/staff/?center={self.center_a.id}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for s in response.data:
            self.assertEqual(s['center_name'], 'Entity A')

    def test_list_all_doctors(self):
        self._auth()
        response = self.client.get('/api/tenants/superadmin/doctors/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_filter_doctors_by_center(self):
        self._auth()
        response = self.client.get(
            f'/api/tenants/superadmin/doctors/?center={self.center_a.id}',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)


# ---------------------------------------------------------------------------
# Deactivated Center Login Block Tests
# ---------------------------------------------------------------------------


class DeactivatedCenterLoginTests(APITestCase):
    """Tests for login rejection when center is deactivated."""

    def setUp(self):
        self.center = make_center('Login Center', 'login-center')
        self.staff_user = make_user('login_staff', email='lstaff@test.com')
        self.staff_user.set_password('testpass123')
        self.staff_user.save()
        make_staff(self.staff_user, self.center, 'Admin')

        self.superuser = make_user(
            'login_super', is_superuser=True, email='lsuper@test.com',
        )
        self.superuser.set_password('testpass123')
        self.superuser.save()

    def test_active_center_allows_login(self):
        response = self.client.post('/api/token/', {
            'username': 'lstaff@test.com',
            'password': 'testpass123',
        }, HTTP_ORIGIN='http://login-center.localhost:8000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_deactivated_center_blocks_login(self):
        self.center.is_active = False
        self.center.save()

        response = self.client.post('/api/token/', {
            'username': 'lstaff@test.com',
            'password': 'testpass123',
        }, HTTP_ORIGIN='http://login-center.localhost:8000')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data['approval_status'], 'CENTER_DEACTIVATED',
        )
        self.assertIn('deactivated', response.data['detail'].lower())

    def test_superadmin_bypasses_deactivated_check(self):
        self.center.is_active = False
        self.center.save()

        response = self.client.post('/api/token/', {
            'username': 'lsuper@test.com',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


# ---------------------------------------------------------------------------
# Deactivated Center Middleware Block Tests
# ---------------------------------------------------------------------------


class DeactivatedCenterMiddlewareTests(APITestCase):
    """Tests for middleware blocking API access for deactivated centers."""

    def setUp(self):
        self.center = make_center('Mw Center', 'mw-center')
        self.staff_user = make_user('mw_staff')
        make_staff(self.staff_user, self.center, 'Admin')

        self.superuser = make_user('mw_super', is_superuser=True)

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults['SERVER_NAME'] = 'mw-center.localhost'

    def test_active_center_allows_api_access(self):
        self._auth(self.staff_user)
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_deactivated_center_blocks_staff_api(self):
        self.center.is_active = False
        self.center.save()
        self._auth(self.staff_user)
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superadmin_bypasses_deactivated_middleware(self):
        self.center.is_active = False
        self.center.save()
        self._auth(self.superuser)
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Self-Registration Center Linking Tests
# ---------------------------------------------------------------------------


class SelfRegistrationCenterLinkTests(APITestCase):
    """Tests for auto-linking patients to center on self-registration."""

    def setUp(self):
        self.center = make_center('Reg Center', 'pop')

    def test_registration_from_subdomain_links_center(self):
        from core.users.models import PatientProfile

        response = self.client.post(
            '/api/auth/register/',
            {
                'password': 'securepass123',
                'confirm_password': 'securepass123',
                'email': 'subdomain_reg@test.com',
                'first_name': 'Sub',
                'last_name': 'Domain',
            },
            HTTP_ORIGIN='http://pop.localhost:5173',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(id=response.data['id'])
        self.assertTrue(hasattr(user, 'patient_profile'))
        profile = user.patient_profile
        self.assertEqual(profile.registered_at_center, self.center)

    def test_registration_from_main_domain_no_center(self):
        from core.users.models import PatientProfile

        response = self.client.post(
            '/api/auth/register/',
            {
                'password': 'securepass123',
                'confirm_password': 'securepass123',
                'email': 'main_reg@test.com',
                'first_name': 'Main',
                'last_name': 'Domain',
            },
            HTTP_ORIGIN='http://localhost:5173',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(id=response.data['id'])
        self.assertTrue(hasattr(user, 'patient_profile'))
        self.assertIsNone(user.patient_profile.registered_at_center)

    def test_registration_from_unknown_subdomain_no_center(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'password': 'securepass123',
                'confirm_password': 'securepass123',
                'email': 'unknown_reg@test.com',
                'first_name': 'Unknown',
                'last_name': 'Sub',
            },
            HTTP_ORIGIN='http://nonexistent.localhost:5173',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(id=response.data['id'])
        self.assertIsNone(user.patient_profile.registered_at_center)

    def test_registration_from_deactivated_center_still_links(self):
        """Registration still links user to a deactivated center.

        Deactivation blocks login, not registration — user is linked
        so that when the center is reactivated they can log in.
        """
        self.center.is_active = False
        self.center.save()

        response = self.client.post(
            '/api/auth/register/',
            {
                'password': 'securepass123',
                'confirm_password': 'securepass123',
                'email': 'deact_reg@test.com',
                'first_name': 'Deact',
                'last_name': 'Center',
            },
            HTTP_ORIGIN='http://pop.localhost:5173',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(id=response.data['id'])
        # Still linked to center — login will be blocked separately
        self.assertEqual(user.patient_profile.registered_at_center, self.center)
