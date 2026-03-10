"""Tests for diagnostics views: PublicReportView, result-history, AnalyticsViewSet."""
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
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
from core.tenants.models import Staff


class PublicReportViewTest(TestCase):
    """Tests for PublicReportView — unauthenticated token-based access."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.tt = make_test_type('CBC', '500.00')
        make_pricing(self.center, self.tt, '500.00')
        self.patient = make_patient('p1', self.center)
        self.order = make_test_order(
            self.patient, self.center, self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        self.report = make_report(
            self.order, self.tt,
            result_data={
                'Hemoglobin': {'value': '14.5', 'unit': 'g/dL', 'ref_range': '13.5-17.5'},
            },
        )

    def test_get_report_by_access_token(self):
        url = f'/api/diagnostics/reports/public/{self.report.access_token}/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['test_type_name'], 'CBC')
        self.assertIn('result_data', resp.data)
        self.assertIn('access_token', resp.data)

    def test_increments_access_count(self):
        url = f'/api/diagnostics/reports/public/{self.report.access_token}/'
        self.client.get(url)
        self.client.get(url)
        self.report.refresh_from_db()
        self.assertEqual(self.report.access_count, 2)

    def test_returns_404_for_invalid_token(self):
        resp = self.client.get(
            '/api/diagnostics/reports/public/00000000-0000-0000-0000-000000000000/'
        )
        self.assertEqual(resp.status_code, 404)

    def test_excludes_deleted_reports(self):
        self.report.is_deleted = True
        self.report.save()
        url = f'/api/diagnostics/reports/public/{self.report.access_token}/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_includes_previous_results_when_available(self):
        # Create a second report for same patient + test type
        order2 = make_test_order(
            self.patient, self.center, self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        report2 = make_report(
            order2, self.tt,
            result_data={
                'Hemoglobin': {'value': '15.0', 'unit': 'g/dL', 'ref_range': '13.5-17.5'},
            },
        )
        url = f'/api/diagnostics/reports/public/{report2.access_token}/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.data.get('previous_results'))
        self.assertIn('date', resp.data['previous_results'])
        self.assertIn('result_data', resp.data['previous_results'])

    def test_no_previous_results_for_first_report(self):
        url = f'/api/diagnostics/reports/public/{self.report.access_token}/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data.get('previous_results'))


class ResultHistoryViewTest(TestCase):
    """Tests for the result-history endpoint on ReportViewSet."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.tt = make_test_type('CBC', '500.00')
        make_pricing(self.center, self.tt, '500.00')
        self.patient = make_patient('p1', self.center)
        self.staff_user = make_user('staff1')
        make_staff(self.staff_user, self.center, role=Staff.Role.LAB_TECHNICIAN)
        self.auth = jwt_auth_header(self.staff_user)

    def test_returns_previous_reports(self):
        order1 = make_test_order(
            self.patient, self.center, self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        make_report(
            order1, self.tt,
            result_data={'Hemoglobin': {'value': '14.5'}},
        )
        order2 = make_test_order(
            self.patient, self.center, self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        make_report(
            order2, self.tt,
            result_data={'Hemoglobin': {'value': '15.0'}},
        )

        url = f'/api/diagnostics/reports/result-history/?patient_id={self.patient.id}&test_type_id={self.tt.id}'
        resp = self.client.get(url, **self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_returns_empty_for_no_history(self):
        url = f'/api/diagnostics/reports/result-history/?patient_id={self.patient.id}&test_type_id={self.tt.id}'
        resp = self.client.get(url, **self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_max_five_results(self):
        for i in range(7):
            order = make_test_order(
                self.patient, self.center, self.tt,
                status=TestOrder.Status.COMPLETED,
            )
            make_report(
                order, self.tt,
                result_data={'Hemoglobin': {'value': str(14 + i)}},
            )
        url = f'/api/diagnostics/reports/result-history/?patient_id={self.patient.id}&test_type_id={self.tt.id}'
        resp = self.client.get(url, **self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 5)

    def test_unauthenticated_denied(self):
        url = f'/api/diagnostics/reports/result-history/?patient_id={self.patient.id}&test_type_id={self.tt.id}'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 401)


class AnalyticsViewSetTest(TestCase):
    """Tests for analytics API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.admin_user = make_user('admin1')
        make_staff(self.admin_user, self.center, role=Staff.Role.ADMIN)
        self.auth = jwt_auth_header(self.admin_user)

        self.tt = make_test_type('CBC', '500.00')
        make_pricing(self.center, self.tt, '500.00')
        self.patient = make_patient('p1', self.center)

    def test_revenue_by_test_endpoint(self):
        make_test_order(
            self.patient, self.center, self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        resp = self.client.get('/api/diagnostics/analytics/revenue-by-test/', **self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)

    def test_revenue_trends_endpoint(self):
        resp = self.client.get('/api/diagnostics/analytics/revenue-trends/', **self.auth)
        self.assertEqual(resp.status_code, 200)

    def test_revenue_by_doctor_endpoint(self):
        resp = self.client.get('/api/diagnostics/analytics/revenue-by-doctor/', **self.auth)
        self.assertEqual(resp.status_code, 200)

    def test_patient_metrics_endpoint(self):
        resp = self.client.get('/api/diagnostics/analytics/patient-metrics/', **self.auth)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('total_patients', resp.data)

    def test_tat_stats_endpoint(self):
        resp = self.client.get('/api/diagnostics/analytics/tat-stats/', **self.auth)
        self.assertEqual(resp.status_code, 200)

    def test_non_admin_denied(self):
        tech_user = make_user('tech1')
        make_staff(tech_user, self.center, role=Staff.Role.LAB_TECHNICIAN)
        tech_auth = jwt_auth_header(tech_user)
        resp = self.client.get('/api/diagnostics/analytics/revenue-by-test/', **tech_auth)
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_denied(self):
        resp = self.client.get('/api/diagnostics/analytics/revenue-by-test/')
        self.assertEqual(resp.status_code, 401)
