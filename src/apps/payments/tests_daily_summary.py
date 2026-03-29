import logging
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.payments.models import Invoice, Payment
from helpers.test_factories import (
    jwt_auth_header,
    make_appointment,
    make_center,
    make_invoice,
    make_invoice_item,
    make_patient,
    make_staff,
    make_user,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Daily Summary API Tests
# ---------------------------------------------------------------------------


class DailySummaryAPITests(APITestCase):
    def setUp(self):
        self.center = make_center()
        self.admin_user = make_user("ds_admin")
        make_staff(self.admin_user, self.center, role="Admin")
        self.staff_user = make_user("ds_staff")
        make_staff(self.staff_user, self.center, role="Receptionist")
        self.admin_headers = jwt_auth_header(self.admin_user)
        self.staff_headers = jwt_auth_header(self.staff_user)

    def _make_invoices(self):
        """Create test invoices for today."""
        patient = make_patient("ds_pat", self.center)

        # Invoice 1: paid
        inv1 = make_invoice(patient, self.center, status=Invoice.Status.PAID)
        make_invoice_item(inv1, unit_price="1000.00")
        inv1.recalculate_totals()

        # Invoice 2: issued (unpaid)
        inv2 = make_invoice(patient, self.center, status=Invoice.Status.ISSUED)
        make_invoice_item(inv2, unit_price="500.00")
        inv2.recalculate_totals()

        # Invoice 3: cancelled (should be excluded)
        inv3 = make_invoice(patient, self.center, status=Invoice.Status.CANCELLED)
        make_invoice_item(inv3, unit_price="200.00")
        inv3.recalculate_totals()

        return inv1, inv2, inv3

    def test_admin_can_access(self):
        resp = self.client.get(
            "/api/payments/daily-summary/",
            **self.admin_headers,
            SERVER_NAME=f"{self.center.domain}.lablink.bd",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_staff_cannot_access(self):
        resp = self.client.get(
            "/api/payments/daily-summary/",
            **self.staff_headers,
            SERVER_NAME=f"{self.center.domain}.lablink.bd",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_daily_summary_totals(self):
        self._make_invoices()
        resp = self.client.get(
            "/api/payments/daily-summary/",
            **self.admin_headers,
            SERVER_NAME=f"{self.center.domain}.lablink.bd",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        # 2 non-cancelled invoices
        self.assertEqual(data["invoice_count"], 2)
        # total invoiced = 1000 + 500 = 1500
        self.assertEqual(Decimal(data["total_invoiced"]), Decimal("1500.00"))
        # 1 paid
        self.assertEqual(data["paid_count"], 1)
        # 1 unpaid
        self.assertEqual(data["unpaid_count"], 1)

    def test_daily_summary_cancelled_excluded(self):
        self._make_invoices()
        resp = self.client.get(
            "/api/payments/daily-summary/",
            **self.admin_headers,
            SERVER_NAME=f"{self.center.domain}.lablink.bd",
        )
        # Cancelled invoice (200) should NOT be in total
        self.assertNotEqual(Decimal(resp.data["total_invoiced"]), Decimal("1700.00"))

    def test_daily_summary_with_date_param(self):
        self._make_invoices()
        # Query a date with no invoices
        resp = self.client.get(
            "/api/payments/daily-summary/",
            {"date": "2020-01-01"},
            **self.admin_headers,
            SERVER_NAME=f"{self.center.domain}.lablink.bd",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["invoice_count"], 0)
        self.assertEqual(Decimal(resp.data["total_invoiced"]), Decimal("0.00"))

    def test_daily_summary_invalid_date(self):
        resp = self.client.get(
            "/api/payments/daily-summary/",
            {"date": "not-a-date"},
            **self.admin_headers,
            SERVER_NAME=f"{self.center.domain}.lablink.bd",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_daily_summary_scoped_to_center(self):
        other_center = make_center("Other", "other")
        other_patient = make_patient("ds_other", other_center)
        inv = make_invoice(other_patient, other_center)
        make_invoice_item(inv, unit_price="999.00")
        inv.recalculate_totals()

        resp = self.client.get(
            "/api/payments/daily-summary/",
            **self.admin_headers,
            SERVER_NAME=f"{self.center.domain}.lablink.bd",
        )
        # Should NOT include other center's data
        self.assertEqual(resp.data["invoice_count"], 0)

    def test_daily_summary_with_payments(self):
        patient = make_patient("ds_pay_pat", self.center)
        appt = make_appointment(patient, self.center)
        inv = make_invoice(patient, self.center, status=Invoice.Status.PAID)
        make_invoice_item(inv, unit_price="2000.00")
        inv.recalculate_totals()

        # Add payment record
        Payment.objects.create(
            appointment=appt,
            invoice=inv,
            amount=Decimal("2000.00"),
            method=Payment.Method.MOBILE_BANKING,
            status=Payment.Status.COMPLETED,
        )

        resp = self.client.get(
            "/api/payments/daily-summary/",
            **self.admin_headers,
            SERVER_NAME=f"{self.center.domain}.lablink.bd",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("by_method", resp.data)
