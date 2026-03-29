import logging
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.payments.models import Invoice, Referrer, ReferrerSettlement
from apps.payments.referrer_services import (
    get_invoice_remaining_commission,
    get_referrer_due_queryset,
)
from helpers.test_factories import (
    jwt_auth_header,
    make_center,
    make_invoice,
    make_invoice_item,
    make_patient,
    make_referrer,
    make_staff,
    make_user,
)

logger = logging.getLogger(__name__)


class ReferrerModelTests(TestCase):
    def setUp(self):
        self.center = make_center()

    def test_str(self):
        referrer = make_referrer(
            self.center,
            name="Dr. Karim",
            commission_pct="15.00",
        )
        self.assertEqual(str(referrer), "Dr. Karim (15.00%)")

    def test_invoice_commission_uses_snapshot(self):
        patient = make_patient("snapshot_pat", self.center)
        referrer = make_referrer(self.center, commission_pct="10.00")
        invoice = make_invoice(
            patient,
            self.center,
            referrer=referrer,
            referrer_name_snapshot=referrer.name,
            commission_pct_snapshot=referrer.commission_pct,
        )
        make_invoice_item(invoice, unit_price="1000.00")
        invoice.recalculate_totals()
        self.assertEqual(invoice.commission_amount, Decimal("100.00"))

        referrer.commission_pct = Decimal("20.00")
        referrer.save(update_fields=["commission_pct"])
        invoice.recalculate_totals()

        self.assertEqual(invoice.commission_pct_snapshot, Decimal("10.00"))
        self.assertEqual(invoice.commission_amount, Decimal("100.00"))

    def test_due_queryset_excludes_unpaid_and_cancelled(self):
        patient = make_patient("due_pat", self.center)
        referrer = make_referrer(self.center, commission_pct="10.00")

        paid_invoice = make_invoice(
            patient,
            self.center,
            status=Invoice.Status.PAID,
            referrer=referrer,
            referrer_name_snapshot=referrer.name,
            commission_pct_snapshot=referrer.commission_pct,
        )
        make_invoice_item(paid_invoice, unit_price="1000.00")
        paid_invoice.recalculate_totals()

        issued_invoice = make_invoice(
            patient,
            self.center,
            status=Invoice.Status.ISSUED,
            referrer=referrer,
            referrer_name_snapshot=referrer.name,
            commission_pct_snapshot=referrer.commission_pct,
        )
        make_invoice_item(issued_invoice, unit_price="500.00")
        issued_invoice.recalculate_totals()

        cancelled_invoice = make_invoice(
            patient,
            self.center,
            status=Invoice.Status.CANCELLED,
            referrer=referrer,
            referrer_name_snapshot=referrer.name,
            commission_pct_snapshot=referrer.commission_pct,
        )
        make_invoice_item(cancelled_invoice, unit_price="700.00")
        cancelled_invoice.recalculate_totals()

        due_invoices = list(get_referrer_due_queryset(referrer, self.center))
        self.assertEqual([invoice.id for invoice in due_invoices], [paid_invoice.id])


class ReferrerAPITests(APITestCase):
    def setUp(self):
        self.center = make_center()
        self.admin_user = make_user("ref_admin")
        make_staff(self.admin_user, self.center, role="Admin")
        self.staff_user = make_user("ref_staff")
        make_staff(self.staff_user, self.center, role="Receptionist")
        self.admin_headers = jwt_auth_header(self.admin_user)
        self.staff_headers = jwt_auth_header(self.staff_user)

    def _server_name(self):
        return f"{self.center.domain}.lablink.bd"

    def test_list_referrers_on_canonical_and_alias_routes(self):
        make_referrer(self.center, name="Dr. ListA")

        canonical = self.client.get(
            "/api/payments/referrers/",
            **self.staff_headers,
            SERVER_NAME=self._server_name(),
        )
        alias = self.client.get(
            "/api/payments/referral-doctors/",
            **self.staff_headers,
            SERVER_NAME=self._server_name(),
        )

        self.assertEqual(canonical.status_code, status.HTTP_200_OK)
        self.assertEqual(alias.status_code, status.HTTP_200_OK)
        canonical_results = canonical.data.get("results", canonical.data)
        alias_results = alias.data.get("results", alias.data)
        self.assertEqual(canonical_results[0]["name"], "Dr. ListA")
        self.assertEqual(alias_results[0]["name"], "Dr. ListA")

    def test_create_referrer_admin_only(self):
        payload = {
            "name": "Agent Rahman",
            "type": Referrer.Type.AGENT,
            "commission_pct": "12.50",
        }
        staff_resp = self.client.post(
            "/api/payments/referrers/",
            payload,
            format="json",
            **self.staff_headers,
            SERVER_NAME=self._server_name(),
        )
        self.assertEqual(staff_resp.status_code, status.HTTP_403_FORBIDDEN)

        admin_resp = self.client.post(
            "/api/payments/referrers/",
            payload,
            format="json",
            **self.admin_headers,
            SERVER_NAME=self._server_name(),
        )
        self.assertEqual(admin_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(admin_resp.data["type"], Referrer.Type.AGENT)

    def test_dropdown_returns_active_only(self):
        make_referrer(self.center, name="Active Referrer")
        make_referrer(
            self.center,
            name="Inactive Referrer",
            phone="01700000123",
            is_active=False,
        )
        resp = self.client.get(
            "/api/payments/referrers/dropdown/",
            **self.staff_headers,
            SERVER_NAME=self._server_name(),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["name"], "Active Referrer")

    def test_create_invoice_with_referrer_id(self):
        patient = make_patient("inv_ref_pat", self.center)
        referrer = make_referrer(self.center, commission_pct="15.00")
        from helpers.test_factories import make_pricing, make_test_type

        test_type = make_test_type("Blood Test", "500.00")
        make_pricing(self.center, test_type)

        resp = self.client.post(
            "/api/payments/invoices/",
            {
                "patient": patient.id,
                "items": [{"test_type_id": test_type.id}],
                "referrer_id": referrer.id,
                "discount_percentage": "0",
            },
            format="json",
            **self.staff_headers,
            SERVER_NAME=self._server_name(),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["referrer"], referrer.id)
        self.assertEqual(resp.data["referrer_name"], referrer.name)
        self.assertEqual(resp.data["referral_doctor"], referrer.id)
        self.assertEqual(resp.data["commission_amount"], "75.00")

    def test_create_invoice_accepts_deprecated_referral_doctor_id(self):
        patient = make_patient("legacy_ref_pat", self.center)
        referrer = make_referrer(self.center, commission_pct="10.00")
        from helpers.test_factories import make_pricing, make_test_type

        test_type = make_test_type("X-Ray", "800.00")
        make_pricing(self.center, test_type)

        resp = self.client.post(
            "/api/payments/invoices/",
            {
                "patient": patient.id,
                "items": [{"test_type_id": test_type.id}],
                "referral_doctor_id": referrer.id,
                "discount_percentage": "0",
            },
            format="json",
            **self.staff_headers,
            SERVER_NAME=self._server_name(),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["referrer"], referrer.id)
        self.assertEqual(resp.data["referral_doctor"], referrer.id)

    def test_ledger_returns_due_only_for_paid_invoices(self):
        referrer = make_referrer(self.center, commission_pct="10.00")
        patient = make_patient("ledger_pat", self.center)

        paid_invoice = make_invoice(
            patient,
            self.center,
            status=Invoice.Status.PAID,
            referrer=referrer,
            referrer_name_snapshot=referrer.name,
            commission_pct_snapshot=referrer.commission_pct,
        )
        make_invoice_item(paid_invoice, unit_price="1000.00")
        paid_invoice.recalculate_totals()

        issued_invoice = make_invoice(
            patient,
            self.center,
            status=Invoice.Status.ISSUED,
            referrer=referrer,
            referrer_name_snapshot=referrer.name,
            commission_pct_snapshot=referrer.commission_pct,
        )
        make_invoice_item(issued_invoice, unit_price="500.00")
        issued_invoice.recalculate_totals()

        resp = self.client.get(
            f"/api/payments/referrers/{referrer.id}/ledger/",
            **self.staff_headers,
            SERVER_NAME=self._server_name(),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["referrer"]["id"], referrer.id)
        self.assertEqual(resp.data["referrer"]["name"], referrer.name)
        self.assertEqual(resp.data["current_due"], "100.00")
        self.assertEqual(resp.data["due_invoice_count"], 1)
        self.assertEqual(len(resp.data["due_invoices"]), 1)
        self.assertEqual(resp.data["due_invoices"][0]["invoice_id"], paid_invoice.id)

    def test_settlement_reduces_due_and_new_paid_invoice_starts_new_due(self):
        referrer = make_referrer(self.center, commission_pct="10.00")
        patient = make_patient("settle_pat", self.center)

        invoice_one = make_invoice(
            patient,
            self.center,
            status=Invoice.Status.PAID,
            referrer=referrer,
            referrer_name_snapshot=referrer.name,
            commission_pct_snapshot=referrer.commission_pct,
        )
        make_invoice_item(invoice_one, unit_price="1000.00")
        invoice_one.recalculate_totals()

        invoice_two = make_invoice(
            patient,
            self.center,
            status=Invoice.Status.PAID,
            referrer=referrer,
            referrer_name_snapshot=referrer.name,
            commission_pct_snapshot=referrer.commission_pct,
        )
        make_invoice_item(invoice_two, unit_price="500.00")
        invoice_two.recalculate_totals()

        full_settlement = self.client.post(
            f"/api/payments/referrers/{referrer.id}/settlements/",
            {
                "invoice_ids": [invoice_one.id, invoice_two.id],
                "amount_paid": "150.00",
                "payment_method": "CASH",
            },
            format="json",
            **self.admin_headers,
            SERVER_NAME=self._server_name(),
        )
        self.assertEqual(full_settlement.status_code, status.HTTP_201_CREATED)

        ledger = self.client.get(
            f"/api/payments/referrers/{referrer.id}/ledger/",
            **self.staff_headers,
            SERVER_NAME=self._server_name(),
        )
        self.assertEqual(ledger.data["current_due"], "0.00")

        invoice_three = make_invoice(
            patient,
            self.center,
            status=Invoice.Status.PAID,
            referrer=referrer,
            referrer_name_snapshot=referrer.name,
            commission_pct_snapshot=referrer.commission_pct,
        )
        make_invoice_item(invoice_three, unit_price="400.00")
        invoice_three.recalculate_totals()

        ledger_after_new = self.client.get(
            f"/api/payments/referrers/{referrer.id}/ledger/",
            **self.staff_headers,
            SERVER_NAME=self._server_name(),
        )
        self.assertEqual(ledger_after_new.data["current_due"], "40.00")
        self.assertEqual(ledger_after_new.data["due_invoice_count"], 1)

    def test_partial_settlement_leaves_remaining_due(self):
        referrer = make_referrer(self.center, commission_pct="10.00")
        patient = make_patient("partial_pat", self.center)
        invoice = make_invoice(
            patient,
            self.center,
            status=Invoice.Status.PAID,
            referrer=referrer,
            referrer_name_snapshot=referrer.name,
            commission_pct_snapshot=referrer.commission_pct,
        )
        make_invoice_item(invoice, unit_price="1000.00")
        invoice.recalculate_totals()

        resp = self.client.post(
            f"/api/payments/referrers/{referrer.id}/settlements/",
            {
                "invoice_ids": [invoice.id],
                "amount_paid": "30.00",
                "payment_method": "BKASH",
            },
            format="json",
            **self.admin_headers,
            SERVER_NAME=self._server_name(),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ReferrerSettlement.objects.count(), 1)
        self.assertEqual(get_invoice_remaining_commission(invoice), Decimal("70.00"))

    def test_legacy_mark_paid_alias_still_functions(self):
        referrer = make_referrer(self.center, commission_pct="10.00")
        patient = make_patient("legacy_mark_paid_pat", self.center)
        invoice = make_invoice(
            patient,
            self.center,
            status=Invoice.Status.PAID,
            referrer=referrer,
            referrer_name_snapshot=referrer.name,
            commission_pct_snapshot=referrer.commission_pct,
        )
        make_invoice_item(invoice, unit_price="1000.00")
        invoice.recalculate_totals()

        resp = self.client.post(
            f"/api/payments/referral-doctors/{referrer.id}/mark-paid/",
            {
                "period_start": invoice.paid_at.date().isoformat(),
                "period_end": invoice.paid_at.date().isoformat(),
                "amount_paid": "100.00",
            },
            format="json",
            **self.admin_headers,
            SERVER_NAME=self._server_name(),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(get_invoice_remaining_commission(invoice), Decimal("0.00"))
