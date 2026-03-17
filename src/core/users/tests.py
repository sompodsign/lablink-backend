import logging

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from core.users.models import PatientProfile
from core.users.serializers import (
    PatientProfileSerializer,
    PatientRegistrationSerializer,
    PatientSerializer,
    UserSerializer,
)
from helpers.test_factories import (
    jwt_auth_header,
    make_center,
    make_doctor,
    make_patient,
    make_staff,
    make_user,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


class UserModelTests(TestCase):
    def test_user_creation_with_phone(self):
        user = make_user("phone_user", phone="01712345678")
        self.assertEqual(user.phone_number, "01712345678")

    def test_patient_profile_str(self):
        center = make_center()
        patient = make_patient("pp_str", center)
        profile = patient.patient_profile
        self.assertEqual(str(profile), "Patient: Pat Ient")

    def test_patient_profile_blood_group_choices(self):
        choices = [c[0] for c in PatientProfile.BloodGroup.choices]
        self.assertIn("A+", choices)
        self.assertIn("O-", choices)
        self.assertEqual(len(choices), 8)

    def test_patient_profile_gender_choices(self):
        choices = [c[0] for c in PatientProfile.Gender.choices]
        self.assertIn("M", choices)
        self.assertIn("F", choices)
        self.assertIn("O", choices)


# ---------------------------------------------------------------------------
# Serializer Tests
# ---------------------------------------------------------------------------


class UserSerializerTests(TestCase):
    def setUp(self):
        self.center = make_center()

    def test_patient_profile_serializer_fields(self):
        patient = make_patient("pp_ser", self.center)
        profile = patient.patient_profile
        serializer = PatientProfileSerializer(profile)
        data = serializer.data
        self.assertIn("phone_number", data)
        self.assertIn("date_of_birth", data)
        self.assertIn("blood_group", data)
        self.assertIn("gender", data)

    def test_patient_serializer_includes_profile(self):
        patient = make_patient("ps_ser", self.center)
        serializer = PatientSerializer(patient)
        data = serializer.data
        self.assertIn("patient_profile", data)
        self.assertEqual(data["full_name"], "Pat Ient")

    def test_user_serializer_hides_password(self):
        user = make_user("hidden_pw")
        serializer = UserSerializer(user)
        self.assertNotIn("password", serializer.data)

    def test_user_serializer_get_staff_role_for_staff(self):
        user = make_user("sr_staff")
        make_staff(user, self.center, "Admin")
        serializer = UserSerializer(user)
        self.assertEqual(serializer.data["staff_role"], "Admin")

    def test_user_serializer_get_staff_role_for_non_staff(self):
        user = make_user("sr_plain")
        serializer = UserSerializer(user)
        self.assertEqual(serializer.data["staff_role"], "")

    def test_user_serializer_get_center_for_staff(self):
        user = make_user("gc_staff")
        make_staff(user, self.center)
        serializer = UserSerializer(user)
        center_data = serializer.data["center"]
        self.assertIsNotNone(center_data)
        self.assertEqual(center_data["name"], "Center A")

    def test_user_serializer_get_center_for_doctor(self):
        user = make_user("gc_doc")
        make_doctor(user, self.center)
        serializer = UserSerializer(user)
        center_data = serializer.data["center"]
        self.assertIsNotNone(center_data)

    def test_user_serializer_get_center_for_patient(self):
        patient = make_patient("gc_pat", self.center)
        serializer = UserSerializer(patient)
        center_data = serializer.data["center"]
        self.assertIsNotNone(center_data)

    def test_user_serializer_get_center_for_superuser_fallback(self):
        user = make_user("gc_super", is_superuser=True)
        serializer = UserSerializer(user)
        center_data = serializer.data["center"]
        # Superadmins have no center
        self.assertIsNone(center_data)

    def test_user_serializer_get_center_none(self):
        user = make_user("gc_none")
        serializer = UserSerializer(user)
        self.assertIsNone(serializer.data["center"])

    def test_role_display_admin(self):
        user = make_user("rd_admin")
        make_staff(user, self.center, "Admin")
        serializer = UserSerializer(user)
        self.assertEqual(serializer.data["role_display"], "Admin")

    def test_role_display_lab_technician(self):
        user = make_user("rd_labtech")
        make_staff(user, self.center, "Lab Technician")
        serializer = UserSerializer(user)
        self.assertEqual(serializer.data["role_display"], "Lab Technician")

    def test_role_display_receptionist(self):
        user = make_user("rd_recep")
        make_staff(user, self.center, "Receptionist")
        serializer = UserSerializer(user)
        self.assertEqual(serializer.data["role_display"], "Receptionist")

    def test_role_display_doctor(self):
        user = make_user("rd_doc")
        make_doctor(user, self.center)
        serializer = UserSerializer(user)
        self.assertEqual(serializer.data["role_display"], "Doctor")

    def test_role_display_superuser(self):
        user = make_user("rd_super", is_superuser=True)
        serializer = UserSerializer(user)
        self.assertEqual(serializer.data["role_display"], "Super Admin")

    def test_role_display_plain_user(self):
        user = make_user("rd_plain")
        serializer = UserSerializer(user)
        self.assertEqual(serializer.data["role_display"], "")

    def test_role_display_patient(self):
        patient = make_patient("rd_patient", self.center)
        serializer = UserSerializer(patient)
        self.assertEqual(serializer.data["role_display"], "")

    def test_registered_user_is_approved(self):
        """Users created via UserSerializer (registration) are approved (patient-only)."""
        data = {
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "email": "newreg@example.com",
            "first_name": "New",
            "last_name": "Reg",
        }
        serializer = UserSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        self.assertTrue(user.is_active)
        self.assertEqual(user.approval_status, User.ApprovalStatus.APPROVED)
        # Username is auto-generated as email__platform
        self.assertTrue(user.username.startswith("newreg@example.com__"))
        self.assertTrue(hasattr(user, "patient_profile"))

    def test_patient_registration_auto_generates_username(self):
        from unittest.mock import MagicMock

        request = MagicMock()
        request.tenant = self.center
        serializer = PatientRegistrationSerializer(
            data={
                "first_name": "Rahim",
                "last_name": "Uddin",
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.first_name, "Rahim")
        self.assertTrue(user.username.startswith("rahim.uddin"))

    def test_patient_registration_duplicate_username_increments(self):
        from unittest.mock import MagicMock

        User.objects.create_user(username="rahim.uddin", password="x")
        request = MagicMock()
        request.tenant = self.center
        serializer = PatientRegistrationSerializer(
            data={"first_name": "Rahim", "last_name": "Uddin"},
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.username, "rahim.uddin1")


# ---------------------------------------------------------------------------
# View Tests
# ---------------------------------------------------------------------------


class RegisterViewTests(APITestCase):
    def test_register_new_user(self):
        payload = {
            "password": "securepass123",
            "confirm_password": "securepass123",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
        }
        response = self.client.post("/api/auth/register/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Username is auto-generated as email__platform
        self.assertTrue(response.data["username"].startswith("new@example.com__"))

    def test_register_missing_required_fields_fails(self):
        payload = {
            "password": "securepass123",
            "confirm_password": "securepass123",
        }
        response = self.client.post("/api/auth/register/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertIn("first_name", response.data)


class UserProfileViewTests(APITestCase):
    def setUp(self):
        self.user = make_user("profile_user", "Pro", "File")

    def test_returns_current_user(self):
        self.client.credentials(**jwt_auth_header(self.user))
        response = self.client.get("/api/auth/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "profile_user")

    def test_requires_auth(self):
        response = self.client.get("/api/auth/profile/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PatientViewTests(APITestCase):
    def setUp(self):
        self.center = make_center()
        self.staff_user = make_user("pv_staff")
        make_staff(self.staff_user, self.center, "Admin")

        self.doctor_user = make_user("pv_doctor")
        make_doctor(self.doctor_user, self.center)

        self.patient = make_patient("pv_patient", self.center)

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def test_staff_can_list_patients(self):
        self._auth(self.staff_user)
        response = self.client.get("/api/auth/patients/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_doctor_can_list_patients(self):
        self._auth(self.doctor_user)
        response = self.client.get("/api/auth/patients/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_can_create_patient(self):
        self._auth(self.staff_user)
        payload = {
            "first_name": "Created",
            "last_name": "Patient",
            "phone_number": "01700000055",
        }
        response = self.client.post("/api/auth/patients/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unauthenticated_denied(self):
        response = self.client.get("/api/auth/patients/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
