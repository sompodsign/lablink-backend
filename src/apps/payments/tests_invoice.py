import logging
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.payments.models import Invoice, InvoiceAuditLog, InvoiceItem
from helpers.test_factories import (
    jwt_auth_header,
    make_appointment,
    make_center,
    make_doctor,
    make_invoice,
    make_invoice_item,
    make_patient,
    make_pricing,
    make_staff,
    make_test_order,
    make_test_type,
    make_user,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


class InvoiceModelTests(TestCase):
    def setUp(self):
        self.center = make_center()
        self.patient = make_patient("inv_model_pat", self.center)

    def test_invoice_auto_generates_number(self):
        invoice = make_invoice(self.patient, self.center)
        self.assertTrue(invoice.invoice_number.startswith("INV-"))
        self.assertIn("-", invoice.invoice_number)

    def test_invoice_str(self):
        invoice = make_invoice(self.patient, self.center)
        result = str(invoice)
        self.assertIn("INV-", result)
        self.assertIn("Pat Ient", result)

    def test_sequential_invoice_numbers(self):
        inv1 = make_invoice(self.patient, self.center)
        inv2 = make_invoice(self.patient, self.center)
        # They should have sequential numbers
        num1 = int(inv1.invoice_number.split("-")[-1])
        num2 = int(inv2.invoice_number.split("-")[-1])
        self.assertEqual(num2, num1 + 1)

    def test_recalculate_totals_no_discount(self):
        invoice = make_invoice(self.patient, self.center)
        make_invoice_item(invoice, unit_price="500.00")
        make_invoice_item(invoice, unit_price="300.00", description="Lipid Panel")
        invoice.recalculate_totals()
        self.assertEqual(invoice.subtotal, Decimal("800.00"))
        self.assertEqual(invoice.discount_amount, Decimal("0.00"))
        self.assertEqual(invoice.total, Decimal("800.00"))

    def test_recalculate_totals_with_discount(self):
        invoice = make_invoice(
            self.patient, self.center, discount_percentage=Decimal("10")
        )
        make_invoice_item(invoice, unit_price="1000.00")
        invoice.recalculate_totals()
        self.assertEqual(invoice.subtotal, Decimal("1000.00"))
        self.assertEqual(invoice.discount_amount, Decimal("100.00"))
        self.assertEqual(invoice.total, Decimal("900.00"))


class InvoiceItemModelTests(TestCase):
    def setUp(self):
        self.center = make_center()
        self.patient = make_patient("inv_item_pat", self.center)
        self.invoice = make_invoice(self.patient, self.center)

    def test_item_auto_calculates_total(self):
        item = make_invoice_item(self.invoice, unit_price="250.00", quantity=2)
        self.assertEqual(item.total_price, Decimal("500.00"))

    def test_item_str(self):
        item = make_invoice_item(self.invoice)
        result = str(item)
        self.assertIn("৳", result)

    def test_visit_fee_item_type(self):
        item = make_invoice_item(
            self.invoice,
            item_type=InvoiceItem.ItemType.VISIT_FEE,
            description="Doctor Visit Fee",
            unit_price="300.00",
        )
        self.assertEqual(item.item_type, "VISIT_FEE")


# ---------------------------------------------------------------------------
# View Tests
# ---------------------------------------------------------------------------


class InvoiceViewTests(APITestCase):
    def setUp(self):
        self.center = make_center(doctor_visit_fee=Decimal("500.00"))
        self.staff_user = make_user("inv_staff")
        make_staff(self.staff_user, self.center, "Admin")

        self.doc_user = make_user("inv_doc")
        make_doctor(self.doc_user, self.center)

        self.patient = make_patient("inv_pat", self.center)
        self.appt = make_appointment(self.patient, self.center)

        self.test_type = make_test_type("Blood Sugar", "400.00")
        make_pricing(self.center, self.test_type, "450.00")
        self.test_order = make_test_order(self.patient, self.center, self.test_type)

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    # ── List ────────────────────────────────────────────────────────

    def test_staff_can_list_invoices(self):
        make_invoice(self.patient, self.center, created_by=self.staff_user)
        self._auth(self.staff_user)
        response = self.client.get("/api/payments/invoices/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_non_staff_denied(self):
        self._auth(self.doc_user)
        response = self.client.get("/api/payments/invoices/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_denied(self):
        response = self.client.get("/api/payments/invoices/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Create ──────────────────────────────────────────────────────

    def test_create_invoice_with_test_orders(self):
        self._auth(self.staff_user)
        payload = {
            "patient": self.patient.id,
            "items": [
                {"test_order_id": self.test_order.id, "item_type": "TEST"},
            ],
            "include_visit_fee": False,
            "discount_percentage": "0",
        }
        response = self.client.post("/api/payments/invoices/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Should use center pricing (450) not base price (400)
        self.assertEqual(Decimal(response.data["subtotal"]), Decimal("450.00"))
        self.assertEqual(Decimal(response.data["total"]), Decimal("450.00"))

    def test_create_invoice_with_visit_fee(self):
        self._auth(self.staff_user)
        payload = {
            "patient": self.patient.id,
            "items": [
                {"test_order_id": self.test_order.id, "item_type": "TEST"},
            ],
            "include_visit_fee": True,
            "discount_percentage": "0",
        }
        response = self.client.post("/api/payments/invoices/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # 450 (test) + 500 (visit fee) = 950
        self.assertEqual(Decimal(response.data["subtotal"]), Decimal("950.00"))

    def test_create_invoice_with_discount(self):
        self._auth(self.staff_user)
        payload = {
            "patient": self.patient.id,
            "items": [
                {"test_order_id": self.test_order.id, "item_type": "TEST"},
            ],
            "include_visit_fee": True,
            "discount_percentage": "10",
        }
        response = self.client.post("/api/payments/invoices/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # subtotal=950, discount=95, total=855
        self.assertEqual(Decimal(response.data["discount_amount"]), Decimal("95.00"))
        self.assertEqual(Decimal(response.data["total"]), Decimal("855.00"))

    def test_create_invoice_falls_back_to_base_price(self):
        """When no CenterTestPricing exists, use TestType.base_price."""
        test_type2 = make_test_type("Urine RE", "200.00")
        order2 = make_test_order(self.patient, self.center, test_type2)

        self._auth(self.staff_user)
        payload = {
            "patient": self.patient.id,
            "items": [
                {"test_order_id": order2.id, "item_type": "TEST"},
            ],
            "include_visit_fee": False,
            "discount_percentage": "0",
        }
        response = self.client.post("/api/payments/invoices/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data["subtotal"]), Decimal("200.00"))

    def test_create_invoice_invalid_discount_over_100(self):
        self._auth(self.staff_user)
        payload = {
            "patient": self.patient.id,
            "items": [],
            "include_visit_fee": True,
            "discount_percentage": "150",
        }
        response = self.client.post("/api/payments/invoices/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Print ───────────────────────────────────────────────────────

    def test_print_data_returns_center_info(self):
        invoice = make_invoice(self.patient, self.center, created_by=self.staff_user)
        make_invoice_item(invoice, unit_price="500.00")
        invoice.recalculate_totals()

        self._auth(self.staff_user)
        response = self.client.get(f"/api/payments/invoices/{invoice.id}/print/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["center_name"], "Center A")
        self.assertIn("items", response.data)
        self.assertEqual(len(response.data["items"]), 1)

    # ── Mark Paid ───────────────────────────────────────────────────

    def test_mark_paid(self):
        invoice = make_invoice(self.patient, self.center)
        self._auth(self.staff_user)
        response = self.client.post(f"/api/payments/invoices/{invoice.id}/mark-paid/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "PAID")

    def test_cannot_mark_cancelled_as_paid(self):
        invoice = make_invoice(
            self.patient, self.center, status=Invoice.Status.CANCELLED
        )
        self._auth(self.staff_user)
        response = self.client.post(f"/api/payments/invoices/{invoice.id}/mark-paid/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Cancel ──────────────────────────────────────────────────────

    def test_cancel_invoice(self):
        invoice = make_invoice(self.patient, self.center)
        self._auth(self.staff_user)
        response = self.client.post(f"/api/payments/invoices/{invoice.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "CANCELLED")

    def test_cannot_cancel_paid_invoice(self):
        invoice = make_invoice(self.patient, self.center, status=Invoice.Status.PAID)
        self._auth(self.staff_user)
        response = self.client.post(f"/api/payments/invoices/{invoice.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Edit (PATCH) ───────────────────────────────────────────────

    def test_edit_issued_invoice_items(self):
        """ISSUED invoice can be edited — items replaced, totals recalculated."""
        invoice = make_invoice(
            self.patient, self.center,
            created_by=self.staff_user,
            status=Invoice.Status.ISSUED,
        )
        make_invoice_item(invoice, unit_price='500.00')
        invoice.recalculate_totals()
        self.assertEqual(invoice.total, Decimal('500.00'))

        self._auth(self.staff_user)
        payload = {
            'items': [
                {'item_type': 'OTHER', 'description': 'Lab Fee', 'unit_price': '300.00', 'quantity': 1},
                {'item_type': 'OTHER', 'description': 'Processing', 'unit_price': '200.00', 'quantity': 1},
            ],
            'reason': 'Correcting line items',
        }
        response = self.client.patch(
            f'/api/payments/invoices/{invoice.id}/', payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 2)
        self.assertEqual(Decimal(response.data['subtotal']), Decimal('500.00'))

    def test_edit_discount(self):
        """Changing discount recalculates totals and creates audit log."""
        invoice = make_invoice(
            self.patient, self.center,
            created_by=self.staff_user,
            status=Invoice.Status.ISSUED,
        )
        make_invoice_item(invoice, unit_price='1000.00')
        invoice.recalculate_totals()

        self._auth(self.staff_user)
        payload = {
            'discount_percentage': '20.00',
            'reason': 'Loyalty discount',
        }
        response = self.client.patch(
            f'/api/payments/invoices/{invoice.id}/', payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['discount_percentage']), Decimal('20.00'))
        self.assertEqual(Decimal(response.data['total']), Decimal('800.00'))

    def test_edit_creates_audit_log(self):
        """Editing creates an InvoiceAuditLog entry."""
        invoice = make_invoice(
            self.patient, self.center,
            created_by=self.staff_user,
            status=Invoice.Status.ISSUED,
        )
        make_invoice_item(invoice, unit_price='500.00')
        invoice.recalculate_totals()

        self._auth(self.staff_user)
        payload = {
            'notes': 'Updated notes',
            'reason': 'Adding note',
        }
        self.client.patch(f'/api/payments/invoices/{invoice.id}/', payload, format='json')
        log = InvoiceAuditLog.objects.filter(invoice=invoice).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action, 'UPDATED')
        self.assertEqual(log.reason, 'Adding note')
        self.assertIn('notes', log.changes)

    def test_cannot_edit_paid_invoice(self):
        invoice = make_invoice(
            self.patient, self.center, status=Invoice.Status.PAID
        )
        self._auth(self.staff_user)
        payload = {'notes': 'change', 'reason': 'test'}
        response = self.client.patch(
            f'/api/payments/invoices/{invoice.id}/', payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_edit_cancelled_invoice(self):
        invoice = make_invoice(
            self.patient, self.center, status=Invoice.Status.CANCELLED
        )
        self._auth(self.staff_user)
        payload = {'notes': 'change', 'reason': 'test'}
        response = self.client.patch(
            f'/api/payments/invoices/{invoice.id}/', payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Audit Log endpoint ─────────────────────────────────────────

    def test_audit_log_endpoint(self):
        """GET /audit-log/ returns change history."""
        invoice = make_invoice(
            self.patient, self.center,
            created_by=self.staff_user,
            status=Invoice.Status.ISSUED,
        )
        InvoiceAuditLog.objects.create(
            invoice=invoice,
            changed_by=self.staff_user,
            action=InvoiceAuditLog.Action.CREATED,
            changes={},
        )
        self._auth(self.staff_user)
        response = self.client.get(f'/api/payments/invoices/{invoice.id}/audit-log/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['action'], 'CREATED')

    def test_mark_paid_creates_audit_log(self):
        """Marking paid creates a STATUS_CHANGED audit entry."""
        invoice = make_invoice(
            self.patient, self.center, status=Invoice.Status.ISSUED
        )
        self._auth(self.staff_user)
        self.client.post(f'/api/payments/invoices/{invoice.id}/mark-paid/')
        log = InvoiceAuditLog.objects.filter(
            invoice=invoice, action='STATUS_CHANGED'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.changes['status']['new'], 'PAID')
