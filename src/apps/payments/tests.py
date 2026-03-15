import logging
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from apps.payments.models import Payment
from apps.payments.serializers import PaymentCreateSerializer, PaymentSerializer
from core.tenants.models import Staff
from helpers.test_factories import (
    jwt_auth_header,
    make_appointment,
    make_center,
    make_doctor,
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


class PaymentModelTests(TestCase):
    def setUp(self):
        self.center = make_center()
        self.patient = make_patient("pay_mod", self.center)
        self.appt = make_appointment(self.patient, self.center)

    def test_payment_str(self):
        payment = Payment.objects.create(
            appointment=self.appt,
            amount="1500.00",
        )
        result = str(payment)
        self.assertIn("1500", result)

    def test_method_choices(self):
        choices = [c[0] for c in Payment.Method.choices]
        self.assertIn("CASH", choices)
        self.assertIn("MOBILE_BANKING", choices)

    def test_status_choices(self):
        choices = [c[0] for c in Payment.Status.choices]
        self.assertIn("PENDING", choices)
        self.assertIn("COMPLETED", choices)
        self.assertIn("FAILED", choices)


# ---------------------------------------------------------------------------
# Serializer Tests
# ---------------------------------------------------------------------------


class PaymentSerializerTests(TestCase):
    def setUp(self):
        self.center = make_center()
        self.patient = make_patient("pay_ser", self.center)
        self.appt = make_appointment(self.patient, self.center)
        self.staff_user = make_user("pay_staff")
        make_staff(self.staff_user, self.center)

    def _mock_request(self):
        from unittest.mock import MagicMock

        request = MagicMock()
        request.tenant = self.center
        request.user = self.staff_user
        return request

    def test_payment_serializer_fields(self):
        payment = Payment.objects.create(
            appointment=self.appt,
            amount="1500.00",
            method="CASH",
            status="COMPLETED",
        )
        serializer = PaymentSerializer(payment)
        data = serializer.data
        self.assertEqual(data["patient_name"], "Pat Ient")
        self.assertEqual(data["method_display"], "Cash")
        self.assertEqual(data["status_display"], "Completed")

    def test_payment_create_validates_appointment_center(self):
        other_center = make_center("Other", "other")
        other_patient = make_patient("other_pay", other_center)
        other_appt = make_appointment(other_patient, other_center)

        request = self._mock_request()
        serializer = PaymentCreateSerializer(
            data={
                "appointment": other_appt.id,
                "amount": "500.00",
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("appointment", serializer.errors)

    def test_payment_create_validates_test_order_center(self):
        other_center = make_center("Other2", "other2")
        test_type = make_test_type()
        make_pricing(other_center, test_type)
        other_patient = make_patient("to_pay", other_center)
        other_order = make_test_order(other_patient, other_center, test_type)

        request = self._mock_request()
        serializer = PaymentCreateSerializer(
            data={
                "appointment": self.appt.id,
                "test_order": other_order.id,
                "amount": "500.00",
            },
            context={"request": request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("test_order", serializer.errors)

    def test_payment_create_allows_null_test_order(self):
        request = self._mock_request()
        serializer = PaymentCreateSerializer(
            data={
                "appointment": self.appt.id,
                "amount": "500.00",
                "method": "CASH",
                "status": "COMPLETED",
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        payment = serializer.save()
        self.assertIsNone(payment.test_order)


# ---------------------------------------------------------------------------
# View Tests
# ---------------------------------------------------------------------------


class PaymentViewTests(APITestCase):
    def setUp(self):
        self.center = make_center()

        self.staff_user = make_user("pv_staff")
        make_staff(self.staff_user, self.center, 'Admin')

        self.doc_user = make_user("pv_doc")
        make_doctor(self.doc_user, self.center)

        self.patient = make_patient("pv_pay", self.center)
        self.appt = make_appointment(self.patient, self.center)

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def test_staff_can_list_payments(self):
        Payment.objects.create(
            appointment=self.appt,
            amount="1500.00",
            method="CASH",
        )
        self._auth(self.staff_user)
        response = self.client.get("/api/payments/payments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_staff_can_create_payment(self):
        self._auth(self.staff_user)
        payload = {
            "appointment": self.appt.id,
            "amount": "2000.00",
            "method": "CASH",
            "status": "COMPLETED",
        }
        response = self.client.post("/api/payments/payments/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data["amount"]), Decimal("2000.00"))

    def test_non_staff_denied(self):
        self._auth(self.doc_user)
        response = self.client.get("/api/payments/payments/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_payment_partial_update(self):
        payment = Payment.objects.create(
            appointment=self.appt,
            amount="1500.00",
            status="PENDING",
        )
        self._auth(self.staff_user)
        response = self.client.patch(
            f"/api/payments/payments/{payment.id}/",
            {"status": "COMPLETED"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "COMPLETED")

    def test_unauthenticated_denied(self):
        response = self.client.get("/api/payments/payments/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
