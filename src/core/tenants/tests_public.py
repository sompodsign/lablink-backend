"""Tests for public-facing landing page API endpoints."""

import logging
from datetime import date, timedelta

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment
from helpers.test_factories import make_center, make_doctor, make_patient, make_user

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PublicCenterView Tests
# ---------------------------------------------------------------------------


class PublicCenterViewTests(APITestCase):
    """GET /api/public/center/?domain=xxx — no auth required."""

    def setUp(self):
        self.center = make_center(
            name="Alpha Lab",
            domain="alpha-lab",
            tagline="Your health, our priority",
        )
        self.url = "/api/public/center/"

    def test_returns_center_by_domain(self):
        resp = self.client.get(self.url, {"domain": "alpha-lab"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "Alpha Lab")
        self.assertEqual(resp.data["domain"], "alpha-lab")
        self.assertEqual(resp.data["tagline"], "Your health, our priority")

    def test_404_for_unknown_domain(self):
        resp = self.client.get(self.url, {"domain": "nonexistent"})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_400_when_missing_domain(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_center_is_hidden(self):
        self.center.is_active = False
        self.center.save()
        resp = self.client.get(self.url, {"domain": "alpha-lab"})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_auth_required(self):
        """Verify endpoint works without any authentication header."""
        resp = self.client.get(self.url, {"domain": "alpha-lab"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# PublicDoctorsView Tests
# ---------------------------------------------------------------------------


class PublicDoctorsViewTests(APITestCase):
    """GET /api/public/doctors/?domain=xxx — no auth required."""

    def setUp(self):
        self.center = make_center(name="Alpha Lab", domain="alpha-lab")
        doctor_user = make_user(
            "doc1",
            first_name="Dr.",
            last_name="House",
            center=self.center,
        )
        self.doctor = make_doctor(doctor_user, self.center)
        self.url = "/api/public/doctors/"

    def test_returns_doctors_for_center(self):
        resp = self.client.get(self.url, {"domain": "alpha-lab"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = (
            resp.data
            if isinstance(resp.data, list)
            else resp.data.get("results", resp.data)
        )
        self.assertGreaterEqual(len(data), 1)
        names = [d["name"] for d in data]
        self.assertIn("Dr. House", names)

    def test_404_for_unknown_domain(self):
        resp = self.client.get(self.url, {"domain": "nope"})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_400_when_missing_domain(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_does_not_return_other_center_doctors(self):
        other_center = make_center(name="Beta Lab", domain="beta-lab")
        other_doc_user = make_user("doc2", center=other_center)
        make_doctor(other_doc_user, other_center)

        resp = self.client.get(self.url, {"domain": "alpha-lab"})
        data = (
            resp.data
            if isinstance(resp.data, list)
            else resp.data.get("results", resp.data)
        )
        user_ids = [d.get("user") for d in data]
        self.assertNotIn(other_doc_user.id, user_ids)


# ---------------------------------------------------------------------------
# PublicBookView Tests
# ---------------------------------------------------------------------------


class PublicBookViewTests(APITestCase):
    """POST /api/public/book/ — guest appointment booking."""

    def setUp(self):
        self.center = make_center(
            name="Alpha Lab",
            domain="alpha-lab",
            allow_online_appointments=True,
        )
        self.url = "/api/public/book/"
        self.tomorrow = (date.today() + timedelta(days=1)).isoformat()

    def _payload(self, **overrides):
        data = {
            "domain": "alpha-lab",
            "guest_name": "Rahim Uddin",
            "guest_phone": "01712345678",
            "date": self.tomorrow,
            "time": "10:00",
            "symptoms": "Headache",
        }
        data.update(overrides)
        return data

    def test_creates_pending_appointment(self):
        resp = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", resp.data)

        appt = Appointment.objects.get(pk=resp.data["id"])
        self.assertEqual(appt.status, "PENDING")
        self.assertEqual(appt.guest_name, "Rahim Uddin")
        self.assertEqual(appt.guest_phone, "01712345678")
        self.assertIsNone(appt.patient)
        self.assertEqual(appt.center, self.center)

    def test_rejects_when_online_appointments_disabled(self):
        self.center.allow_online_appointments = False
        self.center.save()
        resp = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_rejects_past_date(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        resp = self.client.post(self.url, self._payload(date=yesterday), format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date", resp.data)

    def test_rejects_missing_required_fields(self):
        resp = self.client.post(self.url, {"domain": "alpha-lab"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("guest_name", resp.data)
        self.assertIn("guest_phone", resp.data)

    def test_rejects_invalid_domain(self):
        resp = self.client.post(self.url, self._payload(domain="nope"), format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_with_doctor_selection(self):
        doc_user = make_user("doc_book", center=self.center)
        doctor = make_doctor(doc_user, self.center)
        resp = self.client.post(
            self.url, self._payload(doctor=doctor.id), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        appt = Appointment.objects.get(pk=resp.data["id"])
        self.assertEqual(appt.doctor, doctor)

    def test_rejects_doctor_from_other_center(self):
        other = make_center(name="Beta", domain="beta")
        doc_user = make_user("doc_other", center=other)
        doctor = make_doctor(doc_user, other)
        resp = self.client.post(
            self.url, self._payload(doctor=doctor.id), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_auth_required(self):
        resp = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Phone Auto-Linking Tests
# ---------------------------------------------------------------------------


class PhoneAutoLinkTests(TestCase):
    """Auto-linking guest bookings by phone + name."""

    def setUp(self):
        self.center = make_center(
            name="Alpha Lab",
            domain="alpha-lab",
            allow_online_appointments=True,
        )
        self.tomorrow = (date.today() + timedelta(days=1)).isoformat()

    def test_links_when_phone_and_name_match(self):
        """Phone + name match → auto-link to user."""
        existing_user = make_user(
            "existing_pat",
            first_name="Rahim",
            last_name="Uddin",
            phone="01712345678",
            center=self.center,
        )

        resp = self.client.post(
            "/api/public/book/",
            {
                "domain": "alpha-lab",
                "guest_name": "Rahim Uddin",
                "guest_phone": "01712345678",
                "date": self.tomorrow,
                "time": "10:00",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        appt = Appointment.objects.get(pk=resp.json()["id"])
        self.assertEqual(appt.patient, existing_user)
        self.assertEqual(appt.guest_phone, "01712345678")

    def test_no_link_when_phone_matches_but_name_differs(self):
        """Shared family phone — different name → stays unlinked."""
        # Parent exists in the system
        _parent = make_user(
            "parent_user",
            first_name="Karim",
            last_name="Miah",
            phone="01712345678",
            center=self.center,
        )

        # Kid books with same phone but different name
        resp = self.client.post(
            "/api/public/book/",
            {
                "domain": "alpha-lab",
                "guest_name": "Baby Rahim",
                "guest_phone": "01712345678",
                "date": self.tomorrow,
                "time": "10:00",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        appt = Appointment.objects.get(pk=resp.json()["id"])
        # Should NOT auto-link to parent since name doesn't match
        self.assertIsNone(appt.patient)

    def test_stays_unlinked_when_no_matching_user(self):
        """No existing user → patient stays None."""
        resp = self.client.post(
            "/api/public/book/",
            {
                "domain": "alpha-lab",
                "guest_name": "New Person",
                "guest_phone": "01799999999",
                "date": self.tomorrow,
                "time": "09:00",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        appt = Appointment.objects.get(pk=resp.json()["id"])
        self.assertIsNone(appt.patient)

    def test_does_not_link_to_user_at_different_center(self):
        """Phone+name match at a different center should NOT link."""
        other_center = make_center(name="Beta Lab", domain="beta-lab")
        _other_user = make_user(
            "other_center_pat",
            first_name="Rahim",
            last_name="Uddin",
            phone="01712345678",
            center=other_center,
        )

        resp = self.client.post(
            "/api/public/book/",
            {
                "domain": "alpha-lab",
                "guest_name": "Rahim Uddin",
                "guest_phone": "01712345678",
                "date": self.tomorrow,
                "time": "11:00",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        appt = Appointment.objects.get(pk=resp.json()["id"])
        self.assertIsNone(appt.patient)

    def test_registration_claims_matching_name_bookings_only(self):
        """Registration auto-links only bookings with matching name."""
        # Create two orphan guest bookings — same phone, different names
        appt_match = Appointment.objects.create(
            patient=None,
            center=self.center,
            date=date.today() + timedelta(days=2),
            time="10:00",
            status="PENDING",
            guest_name="Karim Miah",
            guest_phone="01811111111",
        )
        appt_kid = Appointment.objects.create(
            patient=None,
            center=self.center,
            date=date.today() + timedelta(days=3),
            time="11:00",
            status="PENDING",
            guest_name="Baby Karim",
            guest_phone="01811111111",
        )

        # Register as 'Karim Miah'
        resp = self.client.post(
            "/api/auth/register/",
            {
                "email": "karim@example.com",
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
                "first_name": "Karim",
                "last_name": "Miah",
                "phone_number": "01811111111",
            },
            content_type="application/json",
            HTTP_HOST="alpha-lab.localhost",
        )
        self.assertEqual(resp.status_code, 201, resp.json())

        # Only the name-matched booking should be linked
        appt_match.refresh_from_db()
        self.assertIsNotNone(appt_match.patient)

        appt_kid.refresh_from_db()
        self.assertIsNone(appt_kid.patient)  # Kid's booking stays unlinked


# ---------------------------------------------------------------------------
# Phone Login Tests
# ---------------------------------------------------------------------------


class PhoneLoginTests(APITestCase):
    """Login with phone number via /api/auth/token/."""

    def setUp(self):
        self.center = make_center(name="Alpha Lab", domain="alpha-lab")
        self.user = make_user(
            "phone_user",
            first_name="Rahim",
            last_name="Uddin",
            phone="01712345678",
            center=self.center,
        )
        self.user.set_password("MyPass123!")
        self.user.save()
        self.url = "/api/token/"

    def test_login_with_phone_number(self):
        resp = self.client.post(
            self.url,
            {"username": "01712345678", "password": "MyPass123!"},
            format="json",
            HTTP_HOST="alpha-lab.localhost",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_phone_wrong_password_fails(self):
        resp = self.client.post(
            self.url,
            {"username": "01712345678", "password": "WrongPass!"},
            format="json",
            HTTP_HOST="alpha-lab.localhost",
        )
        self.assertEqual(resp.status_code, 401)

    def test_shared_phone_password_disambiguates(self):
        """Two users share a phone — correct password picks the right one."""
        other_user = make_user(
            "phone_user2",
            first_name="Fatema",
            last_name="Begum",
            phone="01712345678",
            center=self.center,
        )
        other_user.set_password("OtherPass456!")
        other_user.save()

        # Login with first user's password
        resp = self.client.post(
            self.url,
            {"username": "01712345678", "password": "MyPass123!"},
            format="json",
            HTTP_HOST="alpha-lab.localhost",
        )
        self.assertEqual(resp.status_code, 200)

        # Login with second user's password
        resp2 = self.client.post(
            self.url,
            {"username": "01712345678", "password": "OtherPass456!"},
            format="json",
            HTTP_HOST="alpha-lab.localhost",
        )
        self.assertEqual(resp2.status_code, 200)

    def test_email_login_still_works(self):
        self.user.email = "rahim@example.com"
        self.user.save()
        resp = self.client.post(
            self.url,
            {"username": "rahim@example.com", "password": "MyPass123!"},
            format="json",
            HTTP_HOST="alpha-lab.localhost",
        )
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Throttle Tests
# ---------------------------------------------------------------------------


class CenterBookingThrottleTests(TestCase):
    """CenterBookingThrottle generates per-IP-per-center cache keys."""

    def test_different_centers_get_different_keys(self):
        from unittest.mock import MagicMock

        from core.tenants.throttles import CenterBookingThrottle

        throttle = CenterBookingThrottle()
        throttle.get_ident = MagicMock(return_value="127.0.0.1")

        req_alpha = MagicMock()
        req_alpha.data = {"domain": "alpha-lab"}
        key_alpha = throttle.get_cache_key(req_alpha, None)

        req_beta = MagicMock()
        req_beta.data = {"domain": "beta-lab"}
        key_beta = throttle.get_cache_key(req_beta, None)

        self.assertNotEqual(key_alpha, key_beta)
        self.assertIn("alpha-lab", key_alpha)
        self.assertIn("beta-lab", key_beta)


# ---------------------------------------------------------------------------
# AppointmentSerializer Guest Fields Tests
# ---------------------------------------------------------------------------


class AppointmentSerializerGuestTests(TestCase):
    """Verify serializer handles both patient and guest bookings."""

    def setUp(self):
        self.center = make_center()

    def test_patient_name_for_guest_booking(self):
        from apps.appointments.serializers import AppointmentSerializer

        appt = Appointment.objects.create(
            patient=None,
            center=self.center,
            date="2026-04-01",
            time="10:00",
            status="PENDING",
            guest_name="Guest Person",
            guest_phone="01700000000",
        )
        data = AppointmentSerializer(appt).data
        self.assertEqual(data["patient_name"], "Guest Person")
        self.assertEqual(data["guest_phone"], "01700000000")

    def test_patient_name_for_regular_booking(self):
        from apps.appointments.serializers import AppointmentSerializer

        patient = make_patient("regular_pat", self.center)
        appt = Appointment.objects.create(
            patient=patient,
            center=self.center,
            date="2026-04-01",
            time="10:00",
            status="CONFIRMED",
        )
        data = AppointmentSerializer(appt).data
        self.assertEqual(data["patient_name"], patient.get_full_name())

    def test_patient_name_fallback_to_guest(self):
        """No patient and no guest_name → 'Guest'."""
        from apps.appointments.serializers import AppointmentSerializer

        appt = Appointment.objects.create(
            patient=None,
            center=self.center,
            date="2026-04-01",
            time="10:00",
            status="PENDING",
        )
        data = AppointmentSerializer(appt).data
        self.assertEqual(data["patient_name"], "Guest")
