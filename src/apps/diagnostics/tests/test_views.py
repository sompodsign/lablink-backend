"""Tests for diagnostics views: PublicReportView, result-history, AnalyticsViewSet."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.diagnostics.models import Report, TestOrder
from apps.diagnostics.tokens import make_report_token
from helpers.test_factories import (
    jwt_auth_header,
    make_center,
    make_doctor,
    make_patient,
    make_pricing,
    make_report,
    make_staff,
    make_test_order,
    make_test_type,
    make_user,
)


class PublicReportViewTest(TestCase):
    """Tests for PublicReportView — unauthenticated token-based access."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.tt = make_test_type("CBC", "500.00")
        make_pricing(self.center, self.tt, "500.00")
        self.patient = make_patient("p1", self.center)
        self.order = make_test_order(
            self.patient,
            self.center,
            self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        self.report = make_report(
            self.order,
            self.tt,
            result_data={
                "Hemoglobin": {
                    "value": "14.5",
                    "unit": "g/dL",
                    "ref_range": "13.5-17.5",
                },
            },
        )

    def test_get_report_by_access_token(self):
        """Legacy UUID token still works."""
        url = f"/api/diagnostics/reports/public/{self.report.access_token}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["test_type_name"], "CBC")
        self.assertIn("result_data", resp.data)
        self.assertIn("access_token", resp.data)

    def test_get_report_by_signed_token(self):
        """Signed token returns 200 and correct report."""
        signed = make_report_token(self.report)
        url = f"/api/diagnostics/reports/public/{signed}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["test_type_name"], "CBC")

    def test_expired_signed_token_returns_410(self):
        """Signed token older than 30 days returns HTTP 410."""
        with patch("apps.diagnostics.tokens.verify_report_token") as mock_verify:
            from django.core.signing import SignatureExpired

            mock_verify.side_effect = SignatureExpired()
            # Use a token that looks signed (contains ':')
            resp = self.client.get("/api/diagnostics/reports/public/fake:token/")
        self.assertEqual(resp.status_code, 410)

    def test_tampered_signed_token_returns_403(self):
        """Tampered token returns HTTP 403."""
        with patch("apps.diagnostics.tokens.verify_report_token") as mock_verify:
            from django.core.signing import BadSignature

            mock_verify.side_effect = BadSignature()
            resp = self.client.get("/api/diagnostics/reports/public/tampered:xyz/")
        self.assertEqual(resp.status_code, 403)

    def test_increments_access_count(self):
        url = f"/api/diagnostics/reports/public/{self.report.access_token}/"
        self.client.get(url)
        self.client.get(url)
        self.report.refresh_from_db()
        self.assertEqual(self.report.access_count, 2)

    def test_returns_404_for_invalid_token(self):
        resp = self.client.get(
            "/api/diagnostics/reports/public/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(resp.status_code, 404)

    def test_excludes_deleted_reports(self):
        self.report.is_deleted = True
        self.report.save()
        url = f"/api/diagnostics/reports/public/{self.report.access_token}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_includes_previous_results_when_available(self):
        # Create a second report for same patient + test type
        order2 = make_test_order(
            self.patient,
            self.center,
            self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        report2 = make_report(
            order2,
            self.tt,
            result_data={
                "Hemoglobin": {
                    "value": "15.0",
                    "unit": "g/dL",
                    "ref_range": "13.5-17.5",
                },
            },
        )
        url = f"/api/diagnostics/reports/public/{report2.access_token}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.data.get("previous_results"))
        self.assertIn("date", resp.data["previous_results"])
        self.assertIn("result_data", resp.data["previous_results"])

    def test_no_previous_results_for_first_report(self):
        url = f"/api/diagnostics/reports/public/{self.report.access_token}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data.get("previous_results"))


class ResultHistoryViewTest(TestCase):
    """Tests for the result-history endpoint on ReportViewSet."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.tt = make_test_type("CBC", "500.00")
        make_pricing(self.center, self.tt, "500.00")
        self.patient = make_patient("p1", self.center)
        self.staff_user = make_user("staff1")
        make_staff(self.staff_user, self.center, role="Medical Technologist")
        self.auth = jwt_auth_header(self.staff_user)

    def test_returns_previous_reports(self):
        order1 = make_test_order(
            self.patient,
            self.center,
            self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        make_report(
            order1,
            self.tt,
            result_data={"Hemoglobin": {"value": "14.5"}},
        )
        order2 = make_test_order(
            self.patient,
            self.center,
            self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        make_report(
            order2,
            self.tt,
            result_data={"Hemoglobin": {"value": "15.0"}},
        )

        url = f"/api/diagnostics/reports/result-history/?patient_id={self.patient.id}&test_type_id={self.tt.id}"
        resp = self.client.get(url, **self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_returns_empty_for_no_history(self):
        url = f"/api/diagnostics/reports/result-history/?patient_id={self.patient.id}&test_type_id={self.tt.id}"
        resp = self.client.get(url, **self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_max_five_results(self):
        for i in range(7):
            order = make_test_order(
                self.patient,
                self.center,
                self.tt,
                status=TestOrder.Status.COMPLETED,
            )
            make_report(
                order,
                self.tt,
                result_data={"Hemoglobin": {"value": str(14 + i)}},
            )
        url = f"/api/diagnostics/reports/result-history/?patient_id={self.patient.id}&test_type_id={self.tt.id}"
        resp = self.client.get(url, **self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 5)

    def test_unauthenticated_denied(self):
        url = f"/api/diagnostics/reports/result-history/?patient_id={self.patient.id}&test_type_id={self.tt.id}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 401)


class AnalyticsViewSetTest(TestCase):
    """Tests for analytics API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.admin_user = make_user("admin1")
        make_staff(self.admin_user, self.center, role="Admin")
        self.auth = jwt_auth_header(self.admin_user)

        self.tt = make_test_type("CBC", "500.00")
        make_pricing(self.center, self.tt, "500.00")
        self.patient = make_patient("p1", self.center)

    def test_revenue_by_test_endpoint(self):
        make_test_order(
            self.patient,
            self.center,
            self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        resp = self.client.get(
            "/api/diagnostics/analytics/revenue-by-test/", **self.auth
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)

    def test_revenue_trends_endpoint(self):
        resp = self.client.get(
            "/api/diagnostics/analytics/revenue-trends/", **self.auth
        )
        self.assertEqual(resp.status_code, 200)

    def test_revenue_by_doctor_endpoint(self):
        resp = self.client.get(
            "/api/diagnostics/analytics/revenue-by-doctor/", **self.auth
        )
        self.assertEqual(resp.status_code, 200)

    def test_patient_metrics_endpoint(self):
        resp = self.client.get(
            "/api/diagnostics/analytics/patient-metrics/", **self.auth
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("total_patients", resp.data)

    def test_tat_stats_endpoint(self):
        resp = self.client.get("/api/diagnostics/analytics/tat-stats/", **self.auth)
        self.assertEqual(resp.status_code, 200)

    def test_non_admin_denied(self):
        tech_user = make_user("tech1")
        make_staff(tech_user, self.center, role="Medical Technologist")
        tech_auth = jwt_auth_header(tech_user)
        resp = self.client.get(
            "/api/diagnostics/analytics/revenue-by-test/", **tech_auth
        )
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_denied(self):
        resp = self.client.get("/api/diagnostics/analytics/revenue-by-test/")
        self.assertEqual(resp.status_code, 401)


class DoctorReportAccessTest(TestCase):
    """Tests that doctors can view and print reports for their referred patients."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.tt = make_test_type("CBC", "500.00")
        make_pricing(self.center, self.tt, "500.00")
        self.patient = make_patient("p1", self.center)

        # Doctor user
        self.doc_user = make_user(
            "doc1",
            first_name="Dr. Test",
            last_name="Doctor",
        )
        make_doctor(self.doc_user, self.center)
        self.auth = jwt_auth_header(self.doc_user)

        # Create a report referred by this doctor
        self.order = make_test_order(
            self.patient,
            self.center,
            self.tt,
            status=TestOrder.Status.COMPLETED,
            referring_doctor_name="Dr. Test Doctor",
        )
        self.report = make_report(
            self.order,
            self.tt,
            result_data={
                "Hemoglobin": {
                    "value": "14.5",
                    "unit": "g/dL",
                    "ref_range": "13.5-17.5",
                },
            },
        )

    def test_doctor_can_list_referred_reports(self):
        resp = self.client.get("/api/diagnostics/reports/", **self.auth)
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.report.id)

    def test_doctor_cannot_see_unrelated_reports(self):
        # Create a report referred by a different doctor
        other_order = make_test_order(
            self.patient,
            self.center,
            self.tt,
            status=TestOrder.Status.COMPLETED,
            referring_doctor_name="Dr. Other Person",
        )
        make_report(other_order, self.tt)

        resp = self.client.get("/api/diagnostics/reports/", **self.auth)
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results", resp.data)
        # Should only see their own referred report
        self.assertEqual(len(results), 1)

    def test_doctor_can_retrieve_referred_report(self):
        resp = self.client.get(
            f"/api/diagnostics/reports/{self.report.id}/",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], self.report.id)

    def test_doctor_can_access_print_data(self):
        resp = self.client.get(
            f"/api/diagnostics/reports/{self.report.id}/print-data/",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("result_data", resp.data)
        self.assertIn("center", resp.data)

    def test_doctor_cannot_create_report(self):
        resp = self.client.post(
            "/api/diagnostics/reports/",
            {
                "test_type": self.tt.id,
                "patient": self.patient.id,
                "result_text": "test",
            },
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 403)

    def test_doctor_cannot_update_report(self):
        resp = self.client.patch(
            f"/api/diagnostics/reports/{self.report.id}/",
            {"result_text": "modified"},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 403)

    def test_doctor_cannot_delete_report(self):
        resp = self.client.delete(
            f"/api/diagnostics/reports/{self.report.id}/",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 403)


class LinkedReportCreationTest(TestCase):
    """Tests for creating reports linked to existing test orders."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.tt = make_test_type("CBC", "500.00")
        make_pricing(self.center, self.tt, "500.00")
        self.patient = make_patient("p1", self.center)

        # Lab tech
        self.tech_user = make_user("tech1")
        make_staff(self.tech_user, self.center, role="Medical Technologist")
        self.auth = jwt_auth_header(self.tech_user)

        # Doctor + order
        self.doc_user = make_user(
            "doc1",
            first_name="Dr. Test",
            last_name="Doctor",
        )
        make_doctor(self.doc_user, self.center)
        self.order = make_test_order(
            self.patient,
            self.center,
            self.tt,
            status=TestOrder.Status.PENDING,
            referring_doctor_name="Dr. Test Doctor",
        )

    def test_linked_report_inherits_from_order(self):
        resp = self.client.post(
            "/api/diagnostics/reports/",
            {"test_order": self.order.id, "result_text": "Normal"},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 201)
        report = Report.objects.get(id=resp.data["id"])
        self.assertEqual(report.test_order_id, self.order.id)
        self.assertEqual(report.test_type_id, self.tt.id)
        self.assertEqual(
            report.test_order.referring_doctor_name,
            "Dr. Test Doctor",
        )

    def test_linked_report_marks_order_completed(self):
        self.client.post(
            "/api/diagnostics/reports/",
            {"test_order": self.order.id, "result_text": "Normal"},
            format="json",
            **self.auth,
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, TestOrder.Status.COMPLETED)

    def test_cannot_create_duplicate_report_for_order(self):
        # First report succeeds
        self.client.post(
            "/api/diagnostics/reports/",
            {"test_order": self.order.id, "result_text": "Normal"},
            format="json",
            **self.auth,
        )
        # Second report fails
        resp = self.client.post(
            "/api/diagnostics/reports/",
            {"test_order": self.order.id, "result_text": "Duplicate"},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 400)

    def test_doctor_sees_linked_report(self):
        # Lab tech creates report from doctor's order
        self.client.post(
            "/api/diagnostics/reports/",
            {"test_order": self.order.id, "result_text": "Normal"},
            format="json",
            **self.auth,
        )
        # Doctor checks their reports
        doc_auth = jwt_auth_header(self.doc_user)
        resp = self.client.get("/api/diagnostics/reports/", **doc_auth)
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["referring_doctor_name"],
            "Dr. Test Doctor",
        )


class ResendNotificationTests(TestCase):
    """Tests for resend-email and resend-sms endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.center.email_notifications_enabled = True
        self.center.sms_enabled = True
        self.center.can_use_email = True
        self.center.can_use_sms = True
        self.center.save()

        self.tt = make_test_type("CBC", "500.00")
        make_pricing(self.center, self.tt, "500.00")
        self.patient = make_patient("p1", self.center)
        self.patient.email = "patient@example.com"
        self.patient.phone_number = "01700000001"
        self.patient.save()

        self.admin_user = make_user("admin1")
        make_staff(self.admin_user, self.center, role="Admin")
        self.auth = jwt_auth_header(self.admin_user)

        self.order = make_test_order(
            self.patient,
            self.center,
            self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        self.report = make_report(self.order, self.tt)
        self.report.status = Report.Status.VERIFIED
        self.report.save()

    @patch("apps.diagnostics.services.notifications.send_report_ready_email")
    def test_resend_email_success(self, mock_send):
        mock_send.return_value = True
        resp = self.client.post(
            f"/api/diagnostics/reports/{self.report.id}/resend-email/",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        mock_send.assert_called_once()

    @patch("apps.diagnostics.services.notifications.send_report_ready_sms")
    def test_resend_sms_success(self, mock_send):
        mock_send.return_value = True
        resp = self.client.post(
            f"/api/diagnostics/reports/{self.report.id}/resend-sms/",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        mock_send.assert_called_once()

    def test_resend_email_rejects_draft_report(self):
        self.report.status = Report.Status.DRAFT
        self.report.save()
        resp = self.client.post(
            f"/api/diagnostics/reports/{self.report.id}/resend-email/",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 400)

    def test_resend_sms_rejects_when_sms_disabled(self):
        self.center.sms_enabled = False
        self.center.save()
        resp = self.client.post(
            f"/api/diagnostics/reports/{self.report.id}/resend-sms/",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("not enabled", resp.data["detail"])

    def test_resend_email_rejects_when_no_email(self):
        self.patient.email = ""
        self.patient.save()
        resp = self.client.post(
            f"/api/diagnostics/reports/{self.report.id}/resend-email/",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("no email", resp.data["detail"])

    @patch("core.tenants.throttles.ResendNotificationThrottle.allow_request")
    def test_resend_email_rate_limited(self, mock_allow):
        mock_allow.return_value = False
        resp = self.client.post(
            f"/api/diagnostics/reports/{self.report.id}/resend-email/",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 429)
