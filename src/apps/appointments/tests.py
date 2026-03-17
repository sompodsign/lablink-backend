import logging
from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment
from apps.appointments.serializers import (
    AppointmentSerializer,
    ConsultationUpdateSerializer,
)
from helpers.test_factories import (
    jwt_auth_header,
    make_appointment,
    make_center,
    make_doctor,
    make_patient,
    make_staff,
    make_user,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


class AppointmentModelTests(TestCase):
    def setUp(self):
        self.center = make_center()
        self.patient = make_patient("appt_model", self.center)

    def test_appointment_str(self):
        appt = make_appointment(self.patient, self.center)
        result = str(appt)
        self.assertIn("Center A", result)
        self.assertIn("2026-03-10", result)

    def test_default_status_is_confirmed(self):
        appt = make_appointment(self.patient, self.center)
        self.assertEqual(appt.status, "CONFIRMED")

    def test_status_choices(self):
        choices = [c[0] for c in Appointment.STATUS_CHOICES]
        self.assertIn("CONFIRMED", choices)
        self.assertIn("COMPLETED", choices)
        self.assertIn("CANCELLED", choices)


# ---------------------------------------------------------------------------
# Serializer Tests
# ---------------------------------------------------------------------------


class AppointmentSerializerTests(TestCase):
    def setUp(self):
        self.center = make_center()
        self.patient = make_patient("appt_ser", self.center)
        self.doc_user = make_user("appt_doc", "Dr", "Smith")
        self.doctor = make_doctor(self.doc_user, self.center)

    def test_serializer_includes_patient_name(self):
        appt = make_appointment(self.patient, self.center)
        serializer = AppointmentSerializer(appt)
        self.assertEqual(serializer.data["patient_name"], "Pat Ient")

    def test_serializer_includes_doctor_name(self):
        appt = make_appointment(self.patient, self.center, doctor=self.doctor)
        serializer = AppointmentSerializer(appt)
        self.assertIn("Dr", serializer.data["doctor_name"])

    def test_serializer_doctor_name_empty_when_no_doctor(self):
        appt = make_appointment(self.patient, self.center)
        serializer = AppointmentSerializer(appt)
        self.assertEqual(serializer.data["doctor_name"], "")

    def test_consultation_update_serializer_fields(self):
        appt = make_appointment(self.patient, self.center)
        serializer = ConsultationUpdateSerializer(
            appt,
            data={"symptoms": "Fever", "status": "COMPLETED"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.symptoms, "Fever")
        self.assertEqual(updated.status, "COMPLETED")


# ---------------------------------------------------------------------------
# View Tests
# ---------------------------------------------------------------------------


class AppointmentViewTests(APITestCase):
    def setUp(self):
        self.center = make_center()

        self.staff_user = make_user("appt_staff")
        make_staff(self.staff_user, self.center, "Admin")

        self.doc_user = make_user("appt_view_doc", "Dr", "View")
        self.doctor = make_doctor(self.doc_user, self.center)

        self.patient = make_patient("appt_view_pat", self.center)
        self.appt = make_appointment(
            self.patient,
            self.center,
            doctor=self.doctor,
        )

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def test_staff_sees_all_center_appointments(self):
        self._auth(self.staff_user)
        response = self.client.get("/api/appointments/appointments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_doctor_sees_only_own_appointments(self):
        other_doc_user = make_user("other_doc", "Other", "Doc")
        other_doctor = make_doctor(other_doc_user, self.center)
        make_appointment(self.patient, self.center, doctor=other_doctor)
        self._auth(self.doc_user)
        response = self.client.get("/api/appointments/appointments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for appt in response.data["results"]:
            self.assertEqual(appt["doctor"], self.doctor.id)

    def test_patient_sees_only_own_appointments(self):
        self._auth(self.patient)
        response = self.client.get("/api/appointments/appointments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for appt in response.data["results"]:
            self.assertEqual(appt["patient"], self.patient.id)

    def test_staff_can_create_appointment(self):
        self._auth(self.staff_user)
        payload = {
            "patient": self.patient.id,
            "center": self.center.id,
            "doctor": self.doctor.id,
            "date": "2026-03-15",
            "time": "14:00",
            "symptoms": "Test symptoms",
        }
        response = self.client.post(
            "/api/appointments/appointments/",
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_staff_can_update_appointment(self):
        self._auth(self.staff_user)
        response = self.client.patch(
            f"/api/appointments/appointments/{self.appt.id}/",
            {"status": "CANCELLED"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appt.refresh_from_db()
        self.assertEqual(self.appt.status, "CANCELLED")

    def test_doctor_can_consult(self):
        self._auth(self.doc_user)
        response = self.client.patch(
            f"/api/appointments/appointments/{self.appt.id}/consult/",
            {"symptoms": "Headache and nausea", "status": "COMPLETED"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appt.refresh_from_db()
        self.assertEqual(self.appt.status, "COMPLETED")

    def test_today_endpoint(self):
        # Create an appointment for today
        today_appt = make_appointment(
            self.patient,
            self.center,
            doctor=self.doctor,
            date=date.today().isoformat(),
            time="09:00",
        )
        self._auth(self.doc_user)
        response = self.client.get("/api/appointments/appointments/today/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [a["id"] for a in response.data]
        self.assertIn(today_appt.id, ids)

    def test_unauthenticated_denied(self):
        response = self.client.get("/api/appointments/appointments/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
