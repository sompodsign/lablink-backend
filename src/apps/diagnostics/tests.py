import logging
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.diagnostics.models import (
    CenterTestPricing,
    ReferringDoctor,
    Report,
    TestOrder,
)
from apps.diagnostics.serializers import (
    CenterTestPricingSerializer,
    ReferringDoctorSerializer,
    ReportCreateSerializer,
    ReportPrintSerializer,
    ReportSerializer,
    ReportTemplateSerializer,
    TestOrderCreateSerializer,
    TestOrderSerializer,
    TestOrderStatusUpdateSerializer,
    TestTypeSerializer,
)
from core.tenants.models import Staff
from helpers.test_factories import (
    jwt_auth_header,
    make_appointment,
    make_center,
    make_doctor,
    make_patient,
    make_pricing,
    make_report,
    make_report_template,
    make_staff,
    make_test_order,
    make_test_type,
    make_user,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


class DiagnosticModelTests(TestCase):
    def setUp(self):
        self.center = make_center()
        self.test_type = make_test_type()

    def test_test_type_str(self):
        self.assertEqual(str(self.test_type), "CBC")

    def test_center_test_pricing_str(self):
        pricing = make_pricing(self.center, self.test_type)
        result = str(pricing)
        self.assertIn("Center A", result)
        self.assertIn("CBC", result)

    def test_test_order_str(self):
        patient = make_patient("to_str", self.center)
        order = make_test_order(patient, self.center, self.test_type)
        result = str(order)
        self.assertIn("CBC", result)
        self.assertIn("Pat Ient", result)

    def test_report_str(self):
        patient = make_patient("rp_str", self.center)
        order = make_test_order(patient, self.center, self.test_type)
        report = make_report(order, self.test_type)
        result = str(report)
        self.assertIn("Report", result)

    def test_report_template_str(self):
        template = make_report_template(self.test_type, self.center)
        result = str(template)
        self.assertIn("CBC", result)
        self.assertIn("Center A", result)

    def test_referring_doctor_str(self):
        doc = ReferringDoctor.objects.create(
            center=self.center,
            name="Dr. Test",
        )
        self.assertEqual(str(doc), "Dr. Test")

    def test_test_order_status_choices(self):
        self.assertIn("PENDING", TestOrder.Status.values)
        self.assertIn("IN_PROGRESS", TestOrder.Status.values)
        self.assertIn("COMPLETED", TestOrder.Status.values)
        self.assertIn("CANCELLED", TestOrder.Status.values)

    def test_report_status_choices(self):
        self.assertIn("DRAFT", Report.Status.values)
        self.assertIn("VERIFIED", Report.Status.values)
        self.assertIn("DELIVERED", Report.Status.values)

    def test_test_order_priority_choices(self):
        self.assertIn("NORMAL", TestOrder.Priority.values)
        self.assertIn("URGENT", TestOrder.Priority.values)

    def test_center_test_pricing_unique_together(self):
        make_pricing(self.center, self.test_type)
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            make_pricing(self.center, self.test_type, price="600.00")


# ---------------------------------------------------------------------------
# Serializer Tests
# ---------------------------------------------------------------------------


class DiagnosticSerializerTests(TestCase):
    def setUp(self):
        self.center = make_center()
        self.test_type = make_test_type()
        make_pricing(self.center, self.test_type)
        self.patient = make_patient("ds_pat", self.center)
        self.staff_user = make_user("ds_staff")
        make_staff(self.staff_user, self.center, Staff.Role.LAB_TECHNICIAN)

    def _mock_request(self):
        from unittest.mock import MagicMock

        request = MagicMock()
        request.tenant = self.center
        request.user = self.staff_user
        return request

    def test_test_type_serializer_fields(self):
        serializer = TestTypeSerializer(self.test_type)
        data = serializer.data
        self.assertEqual(data["name"], "CBC")
        self.assertEqual(Decimal(data["base_price"]), Decimal("500.00"))

    def test_center_test_pricing_includes_test_type_details(self):
        pricing = CenterTestPricing.objects.first()
        serializer = CenterTestPricingSerializer(pricing)
        self.assertIn("test_type_details", serializer.data)
        self.assertEqual(serializer.data["test_type_details"]["name"], "CBC")

    def test_report_template_serializer_fields(self):
        template = make_report_template(self.test_type, self.center)
        serializer = ReportTemplateSerializer(template)
        data = serializer.data
        self.assertIn("test_type_name", data)
        self.assertEqual(data["test_type_name"], "CBC")
        self.assertIsInstance(data["fields"], list)

    def test_referring_doctor_serializer_auto_sets_center(self):
        request = self._mock_request()
        serializer = ReferringDoctorSerializer(
            data={"name": "Dr. Amin", "designation": "MBBS"},
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        doc = serializer.save()
        self.assertEqual(doc.center, self.center)

    def test_test_order_serializer_fields(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
            self.staff_user,
        )
        serializer = TestOrderSerializer(order)
        data = serializer.data
        self.assertEqual(data["test_type_name"], "CBC")
        self.assertEqual(data["patient_name"], "Pat Ient")

    def test_test_order_create_validates_test_type_availability(self):
        unavailable_type = make_test_type("Rare Test", "9999.00")
        request = self._mock_request()
        serializer = TestOrderCreateSerializer(
            data={
                "patient": self.patient.id,
                "test_type": unavailable_type.id,
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("test_type", serializer.errors)

    def test_test_order_create_validates_appointment_center(self):
        other_center = make_center("Other", "other")
        other_patient = make_patient("other_p", other_center)
        appt = make_appointment(other_patient, other_center)
        request = self._mock_request()
        serializer = TestOrderCreateSerializer(
            data={
                "patient": self.patient.id,
                "test_type": self.test_type.id,
                "appointment": appt.id,
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("appointment", serializer.errors)

    def test_test_order_create_auto_sets_center_and_created_by(self):
        request = self._mock_request()
        serializer = TestOrderCreateSerializer(
            data={
                "patient": self.patient.id,
                "test_type": self.test_type.id,
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        order = serializer.save()
        self.assertEqual(order.center, self.center)
        self.assertEqual(order.created_by, self.staff_user)

    def test_test_order_status_update_serializer(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
        )
        serializer = TestOrderStatusUpdateSerializer(
            order,
            data={"status": "IN_PROGRESS"},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.status, "IN_PROGRESS")

    def test_report_serializer_fields(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
            self.staff_user,
        )
        report = make_report(order, self.test_type)
        serializer = ReportSerializer(report)
        data = serializer.data
        self.assertEqual(data["test_type_name"], "CBC")
        self.assertEqual(data["patient_name"], "Pat Ient")
        self.assertEqual(data["status_display"], "Draft")

    def test_report_create_auto_creates_test_order(self):
        request = self._mock_request()
        serializer = ReportCreateSerializer(
            data={
                "test_type": self.test_type.id,
                "patient": self.patient.id,
                "referring_doctor_name": "Dr. X",
                "result_text": "All normal",
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        report = serializer.save()
        self.assertIsNotNone(report.test_order)
        self.assertEqual(report.test_order.status, TestOrder.Status.COMPLETED)
        self.assertEqual(report.test_order.patient, self.patient)

    def test_report_create_validates_test_type(self):
        unavailable = make_test_type("Unavail", "100.00")
        request = self._mock_request()
        serializer = ReportCreateSerializer(
            data={
                "test_type": unavailable.id,
                "patient": self.patient.id,
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("test_type", serializer.errors)

    def test_report_print_serializer_fields(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
            self.staff_user,
        )
        report = make_report(order, self.test_type)
        serializer = ReportPrintSerializer(report)
        data = serializer.data
        self.assertIn("center", data)
        self.assertIn("patient", data)
        self.assertIn("lab_technician", data)
        self.assertIn("referring_doctor", data)
        self.assertEqual(data["center"]["name"], "Center A")

    def test_report_print_age_calculation(self):
        from core.users.models import PatientProfile

        patient_user = make_user("aged_pat", "Old", "Patient")
        PatientProfile.objects.create(
            user=patient_user,
            registered_at_center=self.center,
            date_of_birth=date(1990, 1, 1),
        )
        order = make_test_order(
            patient_user,
            self.center,
            self.test_type,
            self.staff_user,
        )
        report = make_report(order, self.test_type)
        serializer = ReportPrintSerializer(report)
        patient_data = serializer.data["patient"]
        self.assertIsNotNone(patient_data["age"])
        self.assertGreater(patient_data["age"], 30)


# ---------------------------------------------------------------------------
# Signal Tests
# ---------------------------------------------------------------------------


class DiagnosticSignalTests(TestCase):
    def setUp(self):
        self.center = make_center()
        self.test_type = make_test_type()
        self.patient = make_user(
            "sig_pat",
            "Sig",
            "Patient",
            phone="01700000001",
        )
        from core.users.models import PatientProfile

        PatientProfile.objects.create(
            user=self.patient,
            registered_at_center=self.center,
            phone_number="01700000001",
        )
        self.appointment = make_appointment(self.patient, self.center)

    @patch("apps.diagnostics.signals.send_sms_notification")
    def test_test_order_created_sends_sms(self, mock_sms):
        TestOrder.objects.create(
            patient=self.patient,
            center=self.center,
            test_type=self.test_type,
        )
        mock_sms.delay.assert_called_once()

    @patch("apps.diagnostics.signals.send_sms_notification")
    def test_test_order_no_phone_skips_sms(self, mock_sms):
        patient_no_phone = make_patient("no_phone", self.center)
        TestOrder.objects.create(
            patient=patient_no_phone,
            center=self.center,
            test_type=self.test_type,
        )
        mock_sms.delay.assert_not_called()

    @patch("apps.diagnostics.signals.send_sms_notification")
    def test_report_created_sends_sms(self, mock_sms):
        order = TestOrder.objects.create(
            patient=self.patient,
            center=self.center,
            test_type=self.test_type,
        )
        mock_sms.delay.reset_mock()
        Report.objects.create(
            test_order=order,
            test_type=self.test_type,
        )
        mock_sms.delay.assert_called_once()

    @patch("apps.diagnostics.signals.send_sms_notification")
    def test_update_does_not_trigger_sms(self, mock_sms):
        order = TestOrder.objects.create(
            patient=self.patient,
            center=self.center,
            test_type=self.test_type,
        )
        mock_sms.delay.reset_mock()
        order.status = TestOrder.Status.IN_PROGRESS
        order.save()
        mock_sms.delay.assert_not_called()


# ---------------------------------------------------------------------------
# View Tests
# ---------------------------------------------------------------------------


class TestTypeViewTests(APITestCase):
    def setUp(self):
        self.test_type = make_test_type()

    def test_list_test_types(self):
        response = self.client.get("/api/diagnostics/test-types/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_test_type(self):
        response = self.client.get(
            f"/api/diagnostics/test-types/{self.test_type.id}/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "CBC")


class TestOrderViewTests(APITestCase):
    def setUp(self):
        self.center = make_center()
        self.test_type = make_test_type()
        make_pricing(self.center, self.test_type)

        self.staff_user = make_user("tov_staff")
        make_staff(self.staff_user, self.center, Staff.Role.ADMIN)

        self.doc_user = make_user("tov_doc")
        self.doctor = make_doctor(self.doc_user, self.center)

        self.lab_tech_user = make_user("tov_tech")
        make_staff(self.lab_tech_user, self.center, Staff.Role.LAB_TECHNICIAN)

        self.patient = make_patient("tov_pat", self.center)
        self.appt = make_appointment(self.patient, self.center, doctor=self.doctor)

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def test_list_test_orders_scoped(self):
        make_test_order(self.patient, self.center, self.test_type)
        self._auth(self.staff_user)
        response = self.client.get("/api/diagnostics/test-orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_doctor_can_create_test_order(self):
        self._auth(self.doc_user)
        payload = {
            "patient": self.patient.id,
            "test_type": self.test_type.id,
            "appointment": self.appt.id,
            "priority": "URGENT",
        }
        response = self.client.post(
            "/api/diagnostics/test-orders/",
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_staff_cannot_create_test_order(self):
        self._auth(self.staff_user)
        payload = {
            "patient": self.patient.id,
            "test_type": self.test_type.id,
        }
        response = self.client.post(
            "/api/diagnostics/test-orders/",
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tech_can_update_status(self):
        order = make_test_order(self.patient, self.center, self.test_type)
        self._auth(self.lab_tech_user)
        response = self.client.patch(
            f"/api/diagnostics/test-orders/{order.id}/",
            {"status": "IN_PROGRESS"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_status(self):
        make_test_order(self.patient, self.center, self.test_type)
        self._auth(self.staff_user)
        response = self.client.get(
            "/api/diagnostics/test-orders/?status=PENDING",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ReportViewTests(APITestCase):
    def setUp(self):
        self.center = make_center()
        self.test_type = make_test_type()
        make_pricing(self.center, self.test_type)

        self.lab_tech_user = make_user("rv_tech")
        make_staff(self.lab_tech_user, self.center, Staff.Role.LAB_TECHNICIAN)

        self.staff_user = make_user("rv_staff")
        make_staff(self.staff_user, self.center, Staff.Role.ADMIN)

        self.patient = make_patient("rv_pat", self.center)

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def test_lab_tech_can_create_report(self):
        self._auth(self.lab_tech_user)
        payload = {
            "test_type": self.test_type.id,
            "patient": self.patient.id,
            "result_text": "Normal values",
        }
        response = self.client.post("/api/diagnostics/reports/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("test_order", response.data)

    def test_staff_cannot_create_report(self):
        self._auth(self.staff_user)
        payload = {
            "test_type": self.test_type.id,
            "patient": self.patient.id,
        }
        response = self.client.post("/api/diagnostics/reports/", payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_report_list_excludes_deleted(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
            self.lab_tech_user,
        )
        report = make_report(order, self.test_type)
        report.is_deleted = True
        report.save()
        self._auth(self.staff_user)
        response = self.client.get("/api/diagnostics/reports/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data["results"]]
        self.assertNotIn(report.id, ids)

    def test_report_soft_delete(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
            self.lab_tech_user,
        )
        report = make_report(order, self.test_type)
        self._auth(self.lab_tech_user)
        response = self.client.delete(
            f"/api/diagnostics/reports/{report.id}/",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        report.refresh_from_db()
        self.assertTrue(report.is_deleted)
        self.assertIsNotNone(report.deleted_at)

    def test_verify_report(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
            self.lab_tech_user,
        )
        report = make_report(order, self.test_type)
        self._auth(self.staff_user)
        response = self.client.post(
            f"/api/diagnostics/reports/{report.id}/verify/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, Report.Status.VERIFIED)
        self.assertEqual(report.verified_by, self.staff_user)

    def test_verify_already_verified_report(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
            self.lab_tech_user,
        )
        report = make_report(order, self.test_type, status=Report.Status.VERIFIED)
        self._auth(self.staff_user)
        response = self.client.post(
            f"/api/diagnostics/reports/{report.id}/verify/",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_print_data_endpoint(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
            self.lab_tech_user,
        )
        report = make_report(order, self.test_type)
        self._auth(self.staff_user)
        response = self.client.get(
            f"/api/diagnostics/reports/{report.id}/print-data/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("center", response.data)
        self.assertIn("patient", response.data)

    def test_patient_sees_only_own_reports(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
            self.lab_tech_user,
        )
        make_report(order, self.test_type)

        other_patient = make_patient("rv_other", self.center)
        other_order = make_test_order(
            other_patient,
            self.center,
            self.test_type,
        )
        make_report(other_order, self.test_type)

        self._auth(self.patient)
        response = self.client.get("/api/diagnostics/reports/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for r in response.data["results"]:
            self.assertEqual(r["patient_name"], "Pat Ient")

    def test_mark_delivered_verified_report(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
            self.lab_tech_user,
        )
        report = make_report(order, self.test_type, status=Report.Status.VERIFIED)
        self._auth(self.staff_user)
        response = self.client.post(
            f"/api/diagnostics/reports/{report.id}/mark-delivered/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, Report.Status.DELIVERED)

    def test_mark_delivered_draft_report_rejected(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
            self.lab_tech_user,
        )
        report = make_report(order, self.test_type)
        self._auth(self.staff_user)
        response = self.client.post(
            f"/api/diagnostics/reports/{report.id}/mark-delivered/",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        report.refresh_from_db()
        self.assertEqual(report.status, Report.Status.DRAFT)

    def test_mark_delivered_already_delivered_rejected(self):
        order = make_test_order(
            self.patient,
            self.center,
            self.test_type,
            self.lab_tech_user,
        )
        report = make_report(order, self.test_type, status=Report.Status.DELIVERED)
        self._auth(self.staff_user)
        response = self.client.post(
            f"/api/diagnostics/reports/{report.id}/mark-delivered/",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ReferringDoctorViewTests(APITestCase):
    def setUp(self):
        self.center = make_center()
        self.staff_user = make_user("rd_staff")
        make_staff(self.staff_user, self.center, Staff.Role.ADMIN)

    def _auth(self):
        self.client.credentials(**jwt_auth_header(self.staff_user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def test_list_referring_doctors(self):
        ReferringDoctor.objects.create(
            center=self.center,
            name="Dr. A",
        )
        self._auth()
        response = self.client.get("/api/diagnostics/referring-doctors/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_referring_doctor(self):
        self._auth()
        payload = {"name": "Dr. New", "designation": "FCPS"}
        response = self.client.post(
            "/api/diagnostics/referring-doctors/",
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            ReferringDoctor.objects.get(name="Dr. New").center,
            self.center,
        )


class ReportTemplateViewTests(APITestCase):
    def setUp(self):
        self.center = make_center()
        self.staff_user = make_user("rt_staff")
        make_staff(self.staff_user, self.center, Staff.Role.ADMIN)
        self.test_type = make_test_type()

    def _auth(self):
        self.client.credentials(**jwt_auth_header(self.staff_user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def test_list_report_templates(self):
        make_report_template(self.test_type, self.center)
        self._auth()
        response = self.client.get("/api/diagnostics/report-templates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_filter_by_test_type(self):
        make_report_template(self.test_type, self.center)
        self._auth()
        response = self.client.get(
            f"/api/diagnostics/report-templates/?test_type={self.test_type.id}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_templates_scoped_to_tenant(self):
        """Templates from center B must not be visible to center A staff."""
        _center_b = make_center("Center B", "center-b")
        # Both centers get auto-created templates via signal.
        # Manually create one more for center A to be thorough.
        make_report_template(
            make_test_type("Custom Test", "100.00"),
            self.center,
        )

        self._auth()
        response = self.client.get("/api/diagnostics/report-templates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Every template returned must belong to center A, not center B
        for template in response.data["results"]:
            self.assertEqual(template["center"], self.center.id)
