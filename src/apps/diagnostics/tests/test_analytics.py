"""Tests for the analytics service."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.diagnostics.models import Report, TestOrder
from apps.diagnostics.services.analytics import (
    patient_metrics,
    revenue_by_doctor,
    revenue_by_test_type,
    revenue_trends,
    turnaround_time_stats,
)
from helpers.test_factories import (
    make_center,
    make_patient,
    make_pricing,
    make_report,
    make_test_order,
    make_test_type,
    make_user,
)


class RevenueByTestTypeTest(TestCase):
    """Tests for revenue_by_test_type."""

    def setUp(self):
        self.center = make_center()
        self.tt_cbc = make_test_type('CBC', '500.00')
        self.tt_xray = make_test_type('X-Ray', '1000.00')
        make_pricing(self.center, self.tt_cbc, '500.00')
        make_pricing(self.center, self.tt_xray, '1000.00')
        self.patient = make_patient('p1', self.center)

    def test_returns_revenue_breakdown(self):
        o1 = make_test_order(
            self.patient, self.center, self.tt_cbc,
            status=TestOrder.Status.COMPLETED,
        )
        o2 = make_test_order(
            self.patient, self.center, self.tt_xray,
            status=TestOrder.Status.COMPLETED,
        )
        data = revenue_by_test_type(self.center)
        self.assertEqual(len(data), 2)
        names = {r['test_type_name'] for r in data}
        self.assertIn('CBC', names)
        self.assertIn('X-Ray', names)

    def test_excludes_pending_orders(self):
        make_test_order(
            self.patient, self.center, self.tt_cbc,
            status=TestOrder.Status.PENDING,
        )
        data = revenue_by_test_type(self.center)
        self.assertEqual(len(data), 0)

    def test_empty_when_no_orders(self):
        data = revenue_by_test_type(self.center)
        self.assertEqual(len(data), 0)


class RevenueTrendsTest(TestCase):
    """Tests for revenue_trends."""

    def setUp(self):
        self.center = make_center()
        self.tt = make_test_type('CBC', '500.00')
        make_pricing(self.center, self.tt, '500.00')
        self.patient = make_patient('p1', self.center)

    def test_returns_daily_points(self):
        make_test_order(
            self.patient, self.center, self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        data = revenue_trends(self.center, period='daily', days=7)
        self.assertGreater(len(data), 0)
        self.assertIn('date', data[0])
        self.assertIn('revenue', data[0])
        self.assertIn('count', data[0])

    def test_empty_when_no_data(self):
        data = revenue_trends(self.center, period='daily', days=7)
        self.assertEqual(len(data), 0)


class RevenueByDoctorTest(TestCase):
    """Tests for revenue_by_doctor."""

    def setUp(self):
        self.center = make_center()
        self.tt = make_test_type('CBC', '500.00')
        make_pricing(self.center, self.tt, '500.00')
        self.patient = make_patient('p1', self.center)

    def test_groups_by_doctor_name(self):
        make_test_order(
            self.patient, self.center, self.tt,
            status=TestOrder.Status.COMPLETED,
            referring_doctor_name='Dr. Karim',
        )
        make_test_order(
            self.patient, self.center, self.tt,
            status=TestOrder.Status.COMPLETED,
            referring_doctor_name='Dr. Karim',
        )
        data = revenue_by_doctor(self.center)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['doctor_name'], 'Dr. Karim')
        self.assertEqual(data[0]['test_count'], 2)

    def test_excludes_orders_without_doctor(self):
        make_test_order(
            self.patient, self.center, self.tt,
            status=TestOrder.Status.COMPLETED,
            referring_doctor_name='',
        )
        data = revenue_by_doctor(self.center)
        self.assertEqual(len(data), 0)


class PatientMetricsTest(TestCase):
    """Tests for patient_metrics."""

    def setUp(self):
        self.center = make_center()
        self.tt = make_test_type('CBC', '500.00')

    def test_counts_new_and_returning(self):
        p1 = make_patient('p1', self.center)
        p2 = make_patient('p2', self.center)

        # p1 had order 90 days ago (before the 30-day window)
        old_order = make_test_order(p1, self.center, self.tt)
        TestOrder.objects.filter(id=old_order.id).update(
            created_at=timezone.now() - timedelta(days=90),
        )
        # p1 also has a recent order → returning
        make_test_order(p1, self.center, self.tt)
        # p2 only has a recent order → new
        make_test_order(p2, self.center, self.tt)

        result = patient_metrics(self.center, days=30)
        self.assertEqual(result['total_patients'], 2)
        self.assertEqual(result['returning_patients'], 1)
        self.assertEqual(result['new_patients'], 1)

    def test_empty_when_no_patients(self):
        result = patient_metrics(self.center, days=30)
        self.assertEqual(result['total_patients'], 0)


class TurnaroundTimeStatsTest(TestCase):
    """Tests for turnaround_time_stats."""

    def setUp(self):
        self.center = make_center()
        self.tt = make_test_type('CBC', '500.00')
        self.patient = make_patient('p1', self.center)

    def test_calculates_tat(self):
        order = make_test_order(
            self.patient, self.center, self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        report = make_report(
            order, self.tt,
            status=Report.Status.VERIFIED,
            verified_at=timezone.now(),
        )
        data = turnaround_time_stats(self.center, days=30)
        self.assertGreater(len(data), 0)
        self.assertEqual(data[0]['test_type_name'], 'CBC')
        self.assertIn('avg_tat_hours', data[0])

    def test_excludes_unverified_reports(self):
        order = make_test_order(
            self.patient, self.center, self.tt,
            status=TestOrder.Status.COMPLETED,
        )
        make_report(order, self.tt, status=Report.Status.DRAFT)
        data = turnaround_time_stats(self.center, days=30)
        self.assertEqual(len(data), 0)

    def test_empty_when_no_reports(self):
        data = turnaround_time_stats(self.center, days=30)
        self.assertEqual(len(data), 0)
