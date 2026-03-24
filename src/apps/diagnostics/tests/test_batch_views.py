"""Tests for batch report operations: batch-print-data, batch-verify."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.diagnostics.models import Report, TestOrder
from helpers.test_factories import (
    jwt_auth_header,
    make_center,
    make_patient,
    make_pricing,
    make_report,
    make_staff,
    make_test_order,
    make_test_type,
    make_user,
)


class BatchPrintDataTest(TestCase):
    """Tests for POST /api/diagnostics/reports/batch-print-data/."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.tt1 = make_test_type("CBC", "500.00")
        self.tt2 = make_test_type("ESR", "300.00")
        make_pricing(self.center, self.tt1, "500.00")
        make_pricing(self.center, self.tt2, "300.00")
        self.patient = make_patient("p1", self.center)

        self.staff_user = make_user("staff1")
        make_staff(self.staff_user, self.center, role="Medical Technologist")
        self.auth = jwt_auth_header(self.staff_user)

        self.order1 = make_test_order(
            self.patient,
            self.center,
            self.tt1,
            status=TestOrder.Status.COMPLETED,
        )
        self.order2 = make_test_order(
            self.patient,
            self.center,
            self.tt2,
            status=TestOrder.Status.COMPLETED,
        )
        self.report1 = make_report(
            self.order1,
            self.tt1,
            result_data={"Hemoglobin": {"value": "14.5", "unit": "g/dL"}},
        )
        self.report2 = make_report(
            self.order2,
            self.tt2,
            result_data={"ESR": {"value": "12", "unit": "mm/hr"}},
        )

    def test_returns_all_selected_reports(self):
        resp = self.client.post(
            "/api/diagnostics/reports/batch-print-data/",
            {"report_ids": [self.report1.id, self.report2.id]},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)
        names = {r["test_type_name"] for r in resp.data}
        self.assertEqual(names, {"CBC", "ESR"})

    def test_rejects_empty_ids(self):
        resp = self.client.post(
            "/api/diagnostics/reports/batch-print-data/",
            {"report_ids": []},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 400)

    def test_rejects_cross_center_reports(self):
        other_center = make_center(name="Other Lab", domain="other-lab")
        other_tt = make_test_type("Lipid", "600.00")
        make_pricing(other_center, other_tt, "600.00")
        other_patient = make_patient("p2", other_center)
        other_order = make_test_order(
            other_patient,
            other_center,
            other_tt,
            status=TestOrder.Status.COMPLETED,
        )
        other_report = make_report(other_order, other_tt)

        resp = self.client.post(
            "/api/diagnostics/reports/batch-print-data/",
            {"report_ids": [self.report1.id, other_report.id]},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 400)

    def test_unauthenticated_denied(self):
        resp = self.client.post(
            "/api/diagnostics/reports/batch-print-data/",
            {"report_ids": [self.report1.id]},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)


class BatchVerifyTest(TestCase):
    """Tests for POST /api/diagnostics/reports/batch-verify/."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.tt1 = make_test_type("CBC", "500.00")
        self.tt2 = make_test_type("ESR", "300.00")
        make_pricing(self.center, self.tt1, "500.00")
        make_pricing(self.center, self.tt2, "300.00")
        self.patient = make_patient("p1", self.center)

        # Admin user (required for verify permission)
        self.admin_user = make_user("admin1")
        make_staff(self.admin_user, self.center, role="Admin")
        self.auth = jwt_auth_header(self.admin_user)

        self.order1 = make_test_order(
            self.patient,
            self.center,
            self.tt1,
            status=TestOrder.Status.COMPLETED,
        )
        self.order2 = make_test_order(
            self.patient,
            self.center,
            self.tt2,
            status=TestOrder.Status.COMPLETED,
        )
        self.report1 = make_report(
            self.order1,
            self.tt1,
            result_data={"Hemoglobin": {"value": "14.5"}},
        )
        self.report2 = make_report(
            self.order2,
            self.tt2,
            result_data={"ESR": {"value": "12"}},
        )

    @patch("apps.diagnostics.views.ReportViewSet._send_verify_notifications")
    def test_verifies_all_draft_reports(self, mock_notify):
        resp = self.client.post(
            "/api/diagnostics/reports/batch-verify/",
            {"report_ids": [self.report1.id, self.report2.id]},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

        self.report1.refresh_from_db()
        self.report2.refresh_from_db()
        self.assertEqual(self.report1.status, Report.Status.VERIFIED)
        self.assertEqual(self.report2.status, Report.Status.VERIFIED)
        self.assertEqual(self.report1.verified_by, self.admin_user)

    @patch("apps.diagnostics.views.ReportViewSet._send_verify_notifications")
    def test_skips_already_verified(self, mock_notify):
        # Pre-verify report1
        self.report1.status = Report.Status.VERIFIED
        self.report1.save(update_fields=["status"])

        resp = self.client.post(
            "/api/diagnostics/reports/batch-verify/",
            {"report_ids": [self.report1.id, self.report2.id]},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

        self.report2.refresh_from_db()
        self.assertEqual(self.report2.status, Report.Status.VERIFIED)

    @patch("apps.diagnostics.views.ReportViewSet._send_verify_notifications")
    def test_sends_email_per_patient(self, mock_notify):
        resp = self.client.post(
            "/api/diagnostics/reports/batch-verify/",
            {"report_ids": [self.report1.id, self.report2.id]},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        # Both reports are for the same patient, so notification method called once
        mock_notify.assert_called_once()

    def test_non_admin_denied(self):
        tech_user = make_user("tech1")
        make_staff(tech_user, self.center, role="Medical Technologist")
        tech_auth = jwt_auth_header(tech_user)

        resp = self.client.post(
            "/api/diagnostics/reports/batch-verify/",
            {"report_ids": [self.report1.id]},
            format="json",
            **tech_auth,
        )
        self.assertEqual(resp.status_code, 403)

    def test_rejects_cross_center_reports(self):
        other_center = make_center(name="Other Lab", domain="other-lab")
        other_tt = make_test_type("Lipid", "600.00")
        make_pricing(other_center, other_tt, "600.00")
        other_patient = make_patient("p2", other_center)
        other_order = make_test_order(
            other_patient,
            other_center,
            other_tt,
            status=TestOrder.Status.COMPLETED,
        )
        other_report = make_report(other_order, other_tt)

        resp = self.client.post(
            "/api/diagnostics/reports/batch-verify/",
            {"report_ids": [self.report1.id, other_report.id]},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 400)
