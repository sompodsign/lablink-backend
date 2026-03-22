import logging
from datetime import date, time

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


# ---------------------------------------------------------------------------
# Patient Online Booking Tests
# ---------------------------------------------------------------------------


class PatientBookingTests(APITestCase):
    """Tests for the patient self-booking endpoint (POST /book/)."""

    def setUp(self):
        self.center = make_center(allow_online_appointments=True)

        # Staff user (admin) — for verifying staff create still works
        self.staff_user = make_user("booking_staff")
        make_staff(self.staff_user, self.center, "Admin")

        # Doctor at this center
        self.doc_user = make_user("booking_doc", "Dr", "Book")
        self.doctor = make_doctor(self.doc_user, self.center)

        # Patient user
        self.patient_user = make_patient("booking_pat", self.center)

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def test_patient_can_book_when_enabled(self):
        self._auth(self.patient_user)
        payload = {
            "doctor": self.doctor.id,
            "date": "2026-06-15",
            "time": "10:00",
            "symptoms": "Headache",
        }
        response = self.client.post("/api/appointments/appointments/book/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertEqual(response.data["patient"], self.patient_user.id)

    def test_patient_cannot_book_when_disabled(self):
        self.center.allow_online_appointments = False
        self.center.save()
        self._auth(self.patient_user)
        payload = {"date": "2026-06-15", "time": "10:00"}
        response = self.client.post("/api/appointments/appointments/book/", payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_booking_creates_pending_status(self):
        self._auth(self.patient_user)
        payload = {"date": "2026-06-15", "time": "14:30"}
        response = self.client.post("/api/appointments/appointments/book/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        appt = Appointment.objects.get(pk=response.data["id"])
        self.assertEqual(appt.status, "PENDING")

    def test_booking_rejects_past_date(self):
        self._auth(self.patient_user)
        payload = {"date": "2020-01-01", "time": "10:00"}
        response = self.client.post("/api/appointments/appointments/book/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date", response.data)

    def test_booking_doctor_must_belong_to_center(self):
        other_center = make_center(
            name="Other Center",
            domain="other",
            allow_online_appointments=True,
        )
        other_doc_user = make_user("other_doc", "Other", "Doc")
        other_doctor = make_doctor(other_doc_user, other_center)

        self._auth(self.patient_user)
        payload = {
            "doctor": other_doctor.id,
            "date": "2026-06-15",
            "time": "10:00",
        }
        response = self.client.post("/api/appointments/appointments/book/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("doctor", response.data)

    def test_booking_without_doctor_succeeds(self):
        self._auth(self.patient_user)
        payload = {"date": "2026-06-15", "time": "09:00", "symptoms": "General checkup"}
        response = self.client.post("/api/appointments/appointments/book/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["doctor"])

    def test_booking_auto_creates_patient_profile(self):
        """Staff user without a PatientProfile gets one auto-created on booking."""
        from core.users.models import PatientProfile

        # Create a user with no patient profile
        plain_user = make_user("no_profile", center=self.center)
        self.assertFalse(PatientProfile.objects.filter(user=plain_user).exists())

        self._auth(plain_user)
        payload = {"date": "2026-06-15", "time": "11:00"}
        response = self.client.post("/api/appointments/appointments/book/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # PatientProfile should now exist
        self.assertTrue(PatientProfile.objects.filter(user=plain_user).exists())
        profile = PatientProfile.objects.get(user=plain_user)
        self.assertEqual(profile.registered_at_center, self.center)

    def test_staff_create_still_works(self):
        """Regular staff appointment creation (POST) is unaffected."""
        self._auth(self.staff_user)
        payload = {
            "patient": self.patient_user.id,
            "center": self.center.id,
            "doctor": self.doctor.id,
            "date": "2026-06-20",
            "time": "15:00",
            "symptoms": "Staff-created",
        }
        response = self.client.post("/api/appointments/appointments/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "CONFIRMED")

    def test_unauthenticated_cannot_book(self):
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"
        payload = {"date": "2026-06-15", "time": "10:00"}
        response = self.client.post("/api/appointments/appointments/book/", payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Auto-Invoice on Completion Tests
# ---------------------------------------------------------------------------


class AutoInvoiceTests(APITestCase):
    """Tests for auto-creating/cancelling invoices on appointment status changes."""

    def setUp(self):
        from decimal import Decimal

        self.center = make_center(
            name="Invoice Center",
            domain="inv-center",
            doctor_visit_fee=Decimal("500.00"),
        )
        # make_center already creates an ACTIVE subscription;
        # no need to create another one.

        self.staff_user = make_user("inv_staff")
        make_staff(self.staff_user, self.center, "Admin")
        self.doc_user = make_user("inv_doc", "Dr", "Invoice")
        self.doctor = make_doctor(self.doc_user, self.center)
        self.doctor.visit_fee = Decimal("500.00")
        self.doctor.save(update_fields=["visit_fee"])
        self.patient = make_patient("inv_pat", self.center)
        self.appt = make_appointment(
            self.patient,
            self.center,
            doctor=self.doctor,
        )

    def tearDown(self):
        from django.core.cache import cache

        cache.clear()

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def _patch_status(self, appt_id, new_status):
        return self.client.patch(
            f"/api/appointments/appointments/{appt_id}/",
            {"status": new_status},
        )

    def test_completing_creates_paid_invoice(self):
        """Marking appointment COMPLETED auto-creates a PAID invoice."""
        from apps.payments.models import Invoice

        self._auth(self.staff_user)
        response = self._patch_status(self.appt.id, "COMPLETED")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        invoices = Invoice.objects.filter(appointment=self.appt)
        self.assertEqual(invoices.count(), 1)
        invoice = invoices.first()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(invoice.patient_id, self.patient.id)

    def test_invoice_includes_visit_fee(self):
        """Auto-invoice includes a VISIT_FEE item for the doctor fee."""
        from decimal import Decimal

        from apps.payments.models import InvoiceItem

        self._auth(self.staff_user)
        self._patch_status(self.appt.id, "COMPLETED")

        items = InvoiceItem.objects.filter(invoice__appointment=self.appt)
        self.assertEqual(items.count(), 1)
        item = items.first()
        self.assertEqual(item.item_type, InvoiceItem.ItemType.VISIT_FEE)
        self.assertEqual(item.unit_price, Decimal("500.00"))

    def test_uncompleting_cancels_invoice(self):
        """Changing status away from COMPLETED cancels the linked invoice."""
        from apps.payments.models import Invoice

        self._auth(self.staff_user)
        self._patch_status(self.appt.id, "COMPLETED")
        self._patch_status(self.appt.id, "CANCELLED")

        invoice = Invoice.objects.filter(appointment=self.appt).first()
        self.assertEqual(invoice.status, Invoice.Status.CANCELLED)

    def test_recompleting_creates_new_invoice(self):
        """Re-completing after cancellation creates a fresh invoice."""
        from apps.payments.models import Invoice

        self._auth(self.staff_user)
        self._patch_status(self.appt.id, "COMPLETED")
        self._patch_status(self.appt.id, "CANCELLED")
        self._patch_status(self.appt.id, "COMPLETED")

        invoices = Invoice.objects.filter(appointment=self.appt)
        self.assertEqual(invoices.count(), 2)
        active = invoices.exclude(status=Invoice.Status.CANCELLED)
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().status, Invoice.Status.PAID)

    def test_no_duplicate_invoice_on_double_complete(self):
        """Completing twice doesn't create a second invoice."""
        from apps.payments.models import Invoice

        self._auth(self.staff_user)
        self._patch_status(self.appt.id, "COMPLETED")

        # Manually PATCH again (status is already COMPLETED)
        self._patch_status(self.appt.id, "COMPLETED")

        invoices = Invoice.objects.filter(appointment=self.appt)
        self.assertEqual(invoices.count(), 1)

    def test_no_visit_fee_without_doctor(self):
        """Appointment without a doctor creates invoice with no items."""
        from apps.payments.models import InvoiceItem

        appt_no_doc = make_appointment(self.patient, self.center)
        self._auth(self.staff_user)
        self._patch_status(appt_no_doc.id, "COMPLETED")

        items = InvoiceItem.objects.filter(invoice__appointment=appt_no_doc)
        self.assertEqual(items.count(), 0)

    def test_invoice_fields_populated(self):
        """Auto-invoice has correct center, notes, and created_by."""
        from apps.payments.models import Invoice

        self._auth(self.staff_user)
        self._patch_status(self.appt.id, "COMPLETED")

        invoice = Invoice.objects.get(appointment=self.appt)
        self.assertEqual(invoice.center, self.center)
        self.assertEqual(invoice.created_by, self.staff_user)
        self.assertIn("Auto-generated", invoice.notes)

    def test_api_response_includes_invoice_fields(self):
        """After completion, the appointment response has invoice_id and invoice_status."""
        self._auth(self.staff_user)
        response = self._patch_status(self.appt.id, "COMPLETED")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data.get("invoice_id"))
        self.assertEqual(response.data.get("invoice_status"), "PAID")


class AvailableSlotsTests(APITestCase):
    """Tests for GET /appointments/appointments/available-slots/."""

    def setUp(self):

        self.center = make_center(
            name="Slot Center",
            domain="slot-center",
        )
        # make_center already creates an ACTIVE subscription;
        # no need to create another one.
        self.staff_user = make_user("slot_staff")
        make_staff(self.staff_user, self.center, "Admin")
        self.doc_user = make_user("slot_doc", "Dr", "Slot")
        self.doctor = make_doctor(self.doc_user, self.center)
        # Set schedule: 09:00–11:00, 30-min slots → 4 slots
        self.doctor.available_from = time(9, 0)
        self.doctor.available_to = time(11, 0)
        self.doctor.slot_duration_minutes = 30
        self.doctor.save()
        self.patient = make_patient("slot_pat", self.center)

    def tearDown(self):
        from django.core.cache import cache

        cache.clear()

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def test_returns_all_slots(self):
        """With no bookings, all slots should be available."""
        self._auth(self.staff_user)
        resp = self.client.get(
            "/api/appointments/appointments/available-slots/",
            {"doctor": self.doctor.id, "date": "2026-04-01"},
        )
        self.assertEqual(resp.status_code, 200)
        slots = resp.data["slots"]
        self.assertEqual(len(slots), 4)  # 09:00, 09:30, 10:00, 10:30
        self.assertTrue(all(s["available"] for s in slots))
        self.assertEqual(slots[0]["time"], "09:00")
        self.assertEqual(slots[-1]["time"], "10:30")

    def test_booked_slot_marked_unavailable(self):
        """An existing appointment marks its slot as unavailable."""
        Appointment.objects.create(
            patient=self.patient,
            center=self.center,
            doctor=self.doctor,
            date=date(2026, 4, 1),
            time=time(9, 30),
            status="CONFIRMED",
        )
        self._auth(self.staff_user)
        resp = self.client.get(
            "/api/appointments/appointments/available-slots/",
            {"doctor": self.doctor.id, "date": "2026-04-01"},
        )
        self.assertEqual(resp.status_code, 200)
        slots = {s["time"]: s["available"] for s in resp.data["slots"]}
        self.assertTrue(slots["09:00"])
        self.assertFalse(slots["09:30"])  # booked
        self.assertTrue(slots["10:00"])

    def test_public_access_with_domain(self):
        """Unauthenticated access works when passing domain param."""
        resp = self.client.get(
            "/api/appointments/appointments/available-slots/",
            {
                "doctor": self.doctor.id,
                "date": "2026-04-01",
                "domain": "slot-center",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["slots"]), 4)

    def test_missing_params_returns_400(self):
        """Missing doctor or date returns 400."""
        self._auth(self.staff_user)
        resp = self.client.get(
            "/api/appointments/appointments/available-slots/",
            {"doctor": self.doctor.id},
        )
        self.assertEqual(resp.status_code, 400)
