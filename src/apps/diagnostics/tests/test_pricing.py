"""Tests for CenterTestPricingViewSet perform_create and read-only center."""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.diagnostics.models import CenterTestPricing
from helpers.test_factories import (
    jwt_auth_header,
    make_center,
    make_doctor,
    make_pricing,
    make_staff,
    make_test_type,
    make_user,
)


class CenterTestPricingViewSetTest(TestCase):
    """Tests for CenterTestPricingViewSet."""

    def setUp(self):
        self.client = APIClient()
        self.center = make_center()
        self.admin = make_user("admin1")
        make_staff(self.admin, self.center, role="Admin")
        self.auth = jwt_auth_header(self.admin)
        self.receptionist = make_user("reception1")
        make_staff(self.receptionist, self.center, role="Receptionist")
        self.reception_auth = jwt_auth_header(self.receptionist)
        self.doctor = make_user("doctor1")
        make_doctor(self.doctor, self.center)
        self.doctor_auth = jwt_auth_header(self.doctor)
        self.tt = make_test_type("CBC", "500.00")

    def test_create_auto_sets_center_from_tenant(self):
        """POST /api/diagnostics/pricing/ should auto-assign the center."""
        resp = self.client.post(
            "/api/diagnostics/pricing/",
            {"test_type": self.tt.id, "price": "600.00"},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 201)
        pricing = CenterTestPricing.objects.get(id=resp.data["id"])
        self.assertEqual(pricing.center_id, self.center.id)
        self.assertEqual(pricing.price, Decimal("600.00"))
        self.assertTrue(pricing.is_available)

    def test_create_without_center_field_succeeds(self):
        """center is read-only; omitting it should not cause a 400."""
        resp = self.client.post(
            "/api/diagnostics/pricing/",
            {"test_type": self.tt.id, "price": "300.00", "is_available": False},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 201)
        pricing = CenterTestPricing.objects.get(id=resp.data["id"])
        self.assertFalse(pricing.is_available)

    def test_list_returns_only_tenant_pricings(self):
        """List endpoint scoped to the requesting tenant."""
        other_center = make_center(name="Beta Lab", domain="beta-lab")
        tt2 = make_test_type("ESR", "200.00")
        make_pricing(self.center, self.tt, "500.00")
        make_pricing(other_center, tt2, "200.00")

        resp = self.client.get("/api/diagnostics/pricing/", **self.auth)
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["test_type"], self.tt.id)

    def test_doctor_can_list_center_pricing(self):
        """Doctors retain read access to center pricing for ordering workflows."""
        make_pricing(self.center, self.tt, "500.00")

        resp = self.client.get("/api/diagnostics/pricing/", **self.doctor_auth)

        self.assertEqual(resp.status_code, 200)

    def test_update_price(self):
        """PATCH should update price."""
        pricing = make_pricing(self.center, self.tt, "500.00")
        resp = self.client.patch(
            f"/api/diagnostics/pricing/{pricing.id}/",
            {"price": "750.00"},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        pricing.refresh_from_db()
        self.assertEqual(pricing.price, Decimal("750.00"))

    def test_delete_pricing(self):
        """DELETE should remove pricing record."""
        pricing = make_pricing(self.center, self.tt, "500.00")
        resp = self.client.delete(
            f"/api/diagnostics/pricing/{pricing.id}/",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(CenterTestPricing.objects.filter(id=pricing.id).exists())

    def test_non_admin_cannot_create_pricing(self):
        """Receptionists can view pricing but cannot create it."""
        resp = self.client.post(
            "/api/diagnostics/pricing/",
            {"test_type": self.tt.id, "price": "300.00"},
            format="json",
            **self.reception_auth,
        )

        self.assertEqual(resp.status_code, 403)

    def test_non_admin_cannot_toggle_availability(self):
        """Only center admins can enable or disable a test."""
        pricing = make_pricing(self.center, self.tt, "500.00", is_available=False)

        resp = self.client.patch(
            f"/api/diagnostics/pricing/{pricing.id}/",
            {"is_available": True},
            format="json",
            **self.reception_auth,
        )

        self.assertEqual(resp.status_code, 403)
        pricing.refresh_from_db()
        self.assertFalse(pricing.is_available)

    def test_unauthenticated_cannot_create(self):
        """Anonymous users cannot create pricing."""
        resp = self.client.post(
            "/api/diagnostics/pricing/",
            {"test_type": self.tt.id, "price": "300.00"},
            format="json",
        )
        self.assertIn(resp.status_code, [401, 403])
