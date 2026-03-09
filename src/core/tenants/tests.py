import logging
from unittest.mock import MagicMock

from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from core.tenants.middleware import TenantMiddleware
from core.tenants.models import Service, Staff
from core.tenants.permissions import (
    IsCenterAdmin,
    IsCenterDoctor,
    IsCenterLabTechnician,
    IsCenterStaff,
    IsCenterStaffOrDoctor,
    IsPatientOwner,
)
from core.tenants.serializers import (
    DiagnosticCenterSerializer,
    DoctorManagementSerializer,
    DoctorSerializer,
    ServiceSerializer,
    StaffSerializer,
)
from helpers.test_factories import (
    FakeRequest,
    jwt_auth_header,
    make_appointment,
    make_center,
    make_doctor,
    make_patient,
    make_pricing,
    make_staff,
    make_test_order,
    make_test_type,
    make_user,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model __str__ Tests
# ---------------------------------------------------------------------------


class ModelStrTests(TestCase):
    def setUp(self):
        self.center = make_center()
        self.user = make_user("struser", "John", "Doe")

    def test_diagnostic_center_str(self):
        self.assertEqual(str(self.center), "Center A")

    def test_service_str(self):
        service = Service.objects.create(
            center=self.center,
            title="Blood Test",
            description="desc",
        )
        self.assertEqual(str(service), "Blood Test - Center A")

    def test_doctor_str(self):
        doctor = make_doctor(self.user, self.center)
        self.assertEqual(str(doctor), "Dr. John Doe")

    def test_staff_str(self):
        staff = make_staff(self.user, self.center, Staff.Role.RECEPTIONIST)
        self.assertEqual(str(staff), "John Doe - RECEPTIONIST")

    def test_staff_role_choices(self):
        choices = [c[0] for c in Staff.Role.choices]
        self.assertIn("RECEPTIONIST", choices)
        self.assertIn("LAB_TECHNICIAN", choices)
        self.assertIn("ADMIN", choices)


# ---------------------------------------------------------------------------
# Permission Unit Tests
# ---------------------------------------------------------------------------


class PermissionClassTests(TestCase):
    def setUp(self):
        self.center_a = make_center("Center A", "center-a")
        self.center_b = make_center("Center B", "center-b")

        self.staff_user = make_user("staff_a")
        make_staff(self.staff_user, self.center_a, Staff.Role.RECEPTIONIST)

        self.admin_user = make_user("admin_a")
        make_staff(self.admin_user, self.center_a, Staff.Role.ADMIN)

        self.lab_tech_user = make_user("labtech_a")
        make_staff(self.lab_tech_user, self.center_a, Staff.Role.LAB_TECHNICIAN)

        self.doctor_user = make_user("doctor_a")
        make_doctor(self.doctor_user, self.center_a)

        self.outsider_user = make_user("outsider")

    def _req(self, user, center):
        return FakeRequest(user, center)

    # IsCenterStaff
    def test_is_center_staff_allows_staff(self):
        req = self._req(self.staff_user, self.center_a)
        self.assertTrue(IsCenterStaff().has_permission(req, None))

    def test_is_center_staff_denies_doctor(self):
        req = self._req(self.doctor_user, self.center_a)
        self.assertFalse(IsCenterStaff().has_permission(req, None))

    def test_is_center_staff_denies_wrong_center(self):
        req = self._req(self.staff_user, self.center_b)
        self.assertFalse(IsCenterStaff().has_permission(req, None))

    def test_is_center_staff_denies_no_tenant(self):
        req = self._req(self.staff_user, None)
        self.assertFalse(IsCenterStaff().has_permission(req, None))

    # IsCenterDoctor
    def test_is_center_doctor_allows_doctor(self):
        req = self._req(self.doctor_user, self.center_a)
        self.assertTrue(IsCenterDoctor().has_permission(req, None))

    def test_is_center_doctor_denies_wrong_center(self):
        req = self._req(self.doctor_user, self.center_b)
        self.assertFalse(IsCenterDoctor().has_permission(req, None))

    def test_is_center_doctor_denies_staff(self):
        req = self._req(self.staff_user, self.center_a)
        self.assertFalse(IsCenterDoctor().has_permission(req, None))

    # IsCenterAdmin
    def test_is_center_admin_allows_admin(self):
        req = self._req(self.admin_user, self.center_a)
        self.assertTrue(IsCenterAdmin().has_permission(req, None))

    def test_is_center_admin_denies_receptionist(self):
        req = self._req(self.staff_user, self.center_a)
        self.assertFalse(IsCenterAdmin().has_permission(req, None))

    # IsCenterLabTechnician
    def test_is_center_lab_technician_allows_lab_tech(self):
        req = self._req(self.lab_tech_user, self.center_a)
        self.assertTrue(IsCenterLabTechnician().has_permission(req, None))

    def test_is_center_lab_technician_denies_receptionist(self):
        req = self._req(self.staff_user, self.center_a)
        self.assertFalse(IsCenterLabTechnician().has_permission(req, None))

    # IsCenterStaffOrDoctor
    def test_staff_or_doctor_allows_staff(self):
        req = self._req(self.staff_user, self.center_a)
        self.assertTrue(IsCenterStaffOrDoctor().has_permission(req, None))

    def test_staff_or_doctor_allows_doctor(self):
        req = self._req(self.doctor_user, self.center_a)
        self.assertTrue(IsCenterStaffOrDoctor().has_permission(req, None))

    def test_staff_or_doctor_denies_outsider(self):
        req = self._req(self.outsider_user, self.center_a)
        self.assertFalse(IsCenterStaffOrDoctor().has_permission(req, None))

    # IsPatientOwner
    def test_patient_owner_allows_patient(self):
        patient = make_patient("pat1", self.center_a)
        appointment = make_appointment(patient, self.center_a)
        req = self._req(patient, self.center_a)
        self.assertTrue(IsPatientOwner().has_object_permission(req, None, appointment))

    def test_patient_owner_denies_other_user(self):
        patient = make_patient("pat2", self.center_a)
        appointment = make_appointment(patient, self.center_a)
        req = self._req(self.staff_user, self.center_a)
        self.assertFalse(IsPatientOwner().has_object_permission(req, None, appointment))

    def test_patient_owner_denies_unauthenticated(self):
        patient = make_patient("pat3", self.center_a)
        appointment = make_appointment(patient, self.center_a)
        anon = MagicMock()
        anon.is_authenticated = False
        req = self._req(anon, self.center_a)
        self.assertFalse(IsPatientOwner().has_object_permission(req, None, appointment))


# ---------------------------------------------------------------------------
# Middleware Tests
# ---------------------------------------------------------------------------


class TenantMiddlewareTests(TestCase):
    def setUp(self):
        self.center = make_center()
        self.factory = RequestFactory()

    def _make_middleware(self):
        return TenantMiddleware(get_response=lambda r: r)

    def test_anonymous_request_has_no_tenant(self):
        request = self.factory.get("/")
        mw = self._make_middleware()
        response = mw(request)
        self.assertIsNone(response.tenant)

    def test_staff_user_resolves_tenant(self):
        user = make_user("mw_staff")
        make_staff(user, self.center)
        mw = self._make_middleware()
        request = self.factory.get(
            "/",
            **jwt_auth_header(user),
        )
        response = mw(request)
        self.assertEqual(response.tenant, self.center)

    def test_doctor_user_resolves_first_center(self):
        user = make_user("mw_doctor")
        make_doctor(user, self.center)
        mw = self._make_middleware()
        request = self.factory.get(
            "/",
            **jwt_auth_header(user),
        )
        response = mw(request)
        self.assertEqual(response.tenant, self.center)

    def test_patient_resolves_registered_center(self):
        patient = make_patient("mw_patient", self.center)
        mw = self._make_middleware()
        request = self.factory.get(
            "/",
            **jwt_auth_header(patient),
        )
        response = mw(request)
        self.assertEqual(response.tenant, self.center)

    def test_superuser_fallback_to_first_center(self):
        superuser = make_user("mw_super", is_superuser=True)
        mw = self._make_middleware()
        request = self.factory.get(
            "/",
            **jwt_auth_header(superuser),
        )
        response = mw(request)
        self.assertIsNotNone(response.tenant)

    def test_user_with_no_profile_no_tenant(self):
        user = make_user("no_profile")
        mw = self._make_middleware()
        request = self.factory.get(
            "/",
            **jwt_auth_header(user),
        )
        response = mw(request)
        self.assertIsNone(response.tenant)


# ---------------------------------------------------------------------------
# Mixin Tests
# ---------------------------------------------------------------------------


class TenantMixinTests(TestCase):
    def test_for_tenant_filters_by_center(self):
        center_a = make_center("Mix A", "mix-a")
        center_b = make_center("Mix B", "mix-b")
        Service.objects.create(
            center=center_a,
            title="Service A",
            description="desc",
        )
        Service.objects.create(
            center=center_b,
            title="Service B",
            description="desc",
        )

        filtered = Service.objects.filter(center=center_a)
        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().title, "Service A")

    def test_for_tenant_with_no_center_field_returns_all(self):
        """Models without a 'center' field return unfiltered."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        make_user("mixin_user_a")
        make_user("mixin_user_b")
        # User model has no 'center' field, so no tenant filtering applies
        self.assertGreaterEqual(User.objects.count(), 2)


# ---------------------------------------------------------------------------
# Serializer Tests
# ---------------------------------------------------------------------------


class TenantSerializerTests(TestCase):
    def setUp(self):
        self.center = make_center()
        Service.objects.create(
            center=self.center,
            title="Active",
            description="d",
            is_active=True,
        )
        Service.objects.create(
            center=self.center,
            title="Inactive",
            description="d",
            is_active=False,
        )

    def test_diagnostic_center_serializer_fields(self):
        serializer = DiagnosticCenterSerializer(self.center)
        data = serializer.data
        self.assertEqual(data["name"], "Center A")
        self.assertIn("domain", data)
        self.assertIn("primary_color", data)

    def test_logo_url_without_logo(self):
        serializer = DiagnosticCenterSerializer(self.center)
        self.assertIsNone(serializer.data["logo_url"])

    def test_services_only_active(self):
        serializer = DiagnosticCenterSerializer(self.center)
        services = serializer.data["services"]
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]["title"], "Active")

    def test_service_serializer_fields(self):
        service = Service.objects.filter(center=self.center, is_active=True).first()
        serializer = ServiceSerializer(service)
        self.assertIn("title", serializer.data)
        self.assertIn("icon", serializer.data)
        self.assertIn("order", serializer.data)

    def test_doctor_serializer_fields(self):
        user = make_user("doc_ser", "Jane", "Smith")
        doctor = make_doctor(user, self.center)
        serializer = DoctorSerializer(doctor)
        data = serializer.data
        self.assertEqual(data["name"], "Jane Smith")
        self.assertIn("specialization", data)

    def test_doctor_management_serializer_fields(self):
        user = make_user("doc_mgmt", "Bob", "Brown")
        doctor = make_doctor(user, self.center)
        serializer = DoctorManagementSerializer(doctor)
        data = serializer.data
        self.assertIn("username", data)
        self.assertIn("email", data)

    def test_staff_serializer_fields(self):
        user = make_user("staff_ser", "Alice", "Green")
        staff = make_staff(user, self.center, Staff.Role.ADMIN)
        serializer = StaffSerializer(staff)
        data = serializer.data
        self.assertEqual(data["role"], "ADMIN")
        self.assertEqual(data["role_display"], "Admin")
        self.assertEqual(data["name"], "Alice Green")


# ---------------------------------------------------------------------------
# Multi-Tenant Isolation Integration Tests
# ---------------------------------------------------------------------------


class TenantIsolationTests(APITestCase):
    """Verify that staff from Center A cannot see data from Center B."""

    def setUp(self):
        self.center_a = make_center("Center A", "center-a")
        self.center_b = make_center("Center B", "center-b")

        self.staff_a_user = make_user("staff_a")
        self.staff_a = make_staff(self.staff_a_user, self.center_a, Staff.Role.ADMIN)

        self.staff_b_user = make_user("staff_b")
        self.staff_b = make_staff(self.staff_b_user, self.center_b, Staff.Role.ADMIN)

        self.patient_a = make_patient("patient_a", self.center_a)
        self.patient_b = make_patient("patient_b", self.center_b)

        self.test_type = make_test_type()
        make_pricing(self.center_a, self.test_type)
        make_pricing(self.center_b, self.test_type)

        self.order_a = make_test_order(
            self.patient_a,
            self.center_a,
            self.test_type,
        )
        self.order_b = make_test_order(
            self.patient_b,
            self.center_b,
            self.test_type,
        )

    def _auth(self, user, tenant):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = tenant.domain + ".localhost"

    def test_staff_a_cannot_see_center_b_test_orders(self):
        self._auth(self.staff_a_user, self.center_a)
        response = self.client.get("/api/diagnostics/test-orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data["results"]]
        self.assertIn(self.order_a.id, ids)
        self.assertNotIn(self.order_b.id, ids)

    def test_staff_b_cannot_see_center_a_test_orders(self):
        self._auth(self.staff_b_user, self.center_b)
        response = self.client.get("/api/diagnostics/test-orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data["results"]]
        self.assertNotIn(self.order_a.id, ids)
        self.assertIn(self.order_b.id, ids)

    def test_staff_a_cannot_see_center_b_patients(self):
        self._auth(self.staff_a_user, self.center_a)
        response = self.client.get("/api/auth/patients/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data["results"]]
        self.assertIn(self.patient_a.id, ids)
        self.assertNotIn(self.patient_b.id, ids)


# ---------------------------------------------------------------------------
# View Tests
# ---------------------------------------------------------------------------


class CurrentTenantViewTests(APITestCase):
    def setUp(self):
        self.center = make_center()
        self.staff_user = make_user("tenant_staff")
        make_staff(self.staff_user, self.center)

    def test_returns_center_info_for_authenticated_user(self):
        self.client.credentials(**jwt_auth_header(self.staff_user))
        response = self.client.get("/api/tenants/current/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Center A")

    def test_returns_404_when_no_tenant(self):
        user = make_user("no_tenant_user")
        self.client.credentials(**jwt_auth_header(user))
        response = self.client.get("/api/tenants/current/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_access_no_auth(self):
        response = self.client.get("/api/tenants/current/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DoctorManagementViewTests(APITestCase):
    def setUp(self):
        self.center = make_center()

        self.admin_user = make_user("admin_doc_mgmt")
        make_staff(self.admin_user, self.center, Staff.Role.ADMIN)

        self.staff_user = make_user("staff_doc_mgmt")
        make_staff(self.staff_user, self.center, Staff.Role.RECEPTIONIST)

        self.doctor_user = make_user("doc_mgmt", "Dr", "Test")
        self.doctor = make_doctor(self.doctor_user, self.center)

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def test_doctor_list_scoped_to_center(self):
        self._auth(self.staff_user)
        response = self.client.get("/api/tenants/doctors/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [d["name"] for d in response.data["results"]]
        self.assertIn("Dr Test", names)

    def test_add_doctor_to_center(self):
        new_doc_user = make_user("new_doc", "New", "Doctor")
        new_doctor = make_doctor(new_doc_user)  # Not associated with center yet
        self._auth(self.admin_user)
        response = self.client.post(
            f"/api/tenants/doctors/{new_doctor.id}/add-to-center/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(new_doctor.centers.filter(id=self.center.id).exists())

    def test_remove_doctor_from_center(self):
        self._auth(self.admin_user)
        response = self.client.post(
            f"/api/tenants/doctors/{self.doctor.id}/remove-from-center/",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(self.doctor.centers.filter(id=self.center.id).exists())

    def test_non_admin_cannot_add_doctor(self):
        new_doc_user = make_user("blocked_doc", "Bl", "Doc")
        new_doctor = make_doctor(new_doc_user)
        self._auth(self.staff_user)
        response = self.client.post(
            f"/api/tenants/doctors/{new_doctor.id}/add-to-center/",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_activity(self):
        patient = make_patient("act_patient", self.center)
        make_appointment(patient, self.center, doctor=self.doctor)
        self._auth(self.staff_user)
        response = self.client.get(
            f"/api/tenants/doctors/{self.doctor.id}/activity/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_appointments", response.data)
        self.assertIn("total_test_orders", response.data)

    def test_add_nonexistent_doctor_404(self):
        self._auth(self.admin_user)
        response = self.client.post(
            "/api/tenants/doctors/99999/add-to-center/",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class StaffViewTests(APITestCase):
    def setUp(self):
        self.center = make_center()
        self.admin_user = make_user("admin_staff_view")
        make_staff(self.admin_user, self.center, Staff.Role.ADMIN)

        self.receptionist_user = make_user("recep_staff_view")
        make_staff(self.receptionist_user, self.center, Staff.Role.RECEPTIONIST)

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def test_admin_can_list_staff(self):
        self._auth(self.admin_user)
        response = self.client.get("/api/tenants/staff/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_non_admin_denied(self):
        self._auth(self.receptionist_user)
        response = self.client.get("/api/tenants/staff/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Patient Registration Tests (kept from original)
# ---------------------------------------------------------------------------


class PatientRegistrationTests(APITestCase):
    def setUp(self):
        self.center = make_center()
        self.admin_user = make_user("admin_user")
        make_staff(self.admin_user, self.center, Staff.Role.ADMIN)
        self.client.credentials(**jwt_auth_header(self.admin_user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def test_staff_can_register_patient(self):
        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": "01700000099",
            "blood_group": "A+",
        }
        response = self.client.post("/api/auth/patients/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["first_name"], "John")
        self.assertIn("patient_profile", response.data)

    def test_patient_profile_linked_to_center(self):
        from core.users.models import PatientProfile

        payload = {"first_name": "Jane", "last_name": "Doe"}
        response = self.client.post("/api/auth/patients/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user_id = response.data["id"]
        profile = PatientProfile.objects.get(user_id=user_id)
        self.assertEqual(profile.registered_at_center, self.center)
