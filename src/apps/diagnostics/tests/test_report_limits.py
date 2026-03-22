import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.diagnostics.models import Report
from apps.subscriptions.models import Subscription, SubscriptionPlan
from helpers.test_factories import (
    jwt_auth_header,
    make_center,
    make_patient,
    make_pricing,
    make_staff,
    make_test_type,
    make_user,
)

logger = logging.getLogger(__name__)


class ReportLimitTests(APITestCase):
    """Tests for monthly report limit enforcement."""

    def setUp(self):
        self.center = make_center()
        self.test_type = make_test_type()
        make_pricing(self.center, self.test_type)

        self.lab_tech_user = make_user("rl_tech")
        make_staff(self.lab_tech_user, self.center, "Medical Technologist")

        self.patient = make_patient("rl_pat", self.center)

        # Update the subscription created by make_center with a limited plan
        self.plan = SubscriptionPlan.objects.create(
            name="Test Limit Plan",
            slug="test-limit-plan",
            price=999,
            max_staff=5,
            max_reports=3,
        )
        Subscription.objects.filter(center=self.center).update(
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
        )
        self.sub = Subscription.objects.get(center=self.center)

    def _auth(self):
        self.client.credentials(**jwt_auth_header(self.lab_tech_user))
        self.client.defaults["SERVER_NAME"] = self.center.domain + ".localhost"

    def _create_report_payload(self):
        return {
            "test_type": self.test_type.id,
            "patient": self.patient.id,
            "result_text": "Normal",
        }

    def test_report_creation_allowed_within_limit(self):
        """Reports can be created when under the monthly limit."""
        self._auth()
        for _ in range(3):
            response = self.client.post(
                "/api/diagnostics/reports/",
                self._create_report_payload(),
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_report_creation_blocked_at_limit(self):
        """Report creation returns 403 when monthly limit reached."""
        self._auth()
        # Create 3 reports (the limit)
        for _ in range(3):
            resp = self.client.post(
                "/api/diagnostics/reports/",
                self._create_report_payload(),
            )
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # 4th should be blocked
        response = self.client.post(
            "/api/diagnostics/reports/",
            self._create_report_payload(),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("report limit", response.data["detail"].lower())

    def test_unlimited_reports_plan(self):
        """Plans with max_reports=-1 allow unlimited reports."""
        self.plan.max_reports = -1
        self.plan.save()
        self._auth()
        for _ in range(5):
            response = self.client.post(
                "/api/diagnostics/reports/",
                self._create_report_payload(),
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_report_limit_resets_monthly(self):
        """Reports from previous months don't count toward the limit."""
        self._auth()
        # Create 3 reports (at the limit)
        for _ in range(3):
            self.client.post(
                "/api/diagnostics/reports/",
                self._create_report_payload(),
            )

        # Backdate all to last month
        last_month = timezone.now() - timedelta(days=35)
        Report.objects.filter(
            test_order__center=self.center,
        ).update(created_at=last_month)

        # Now a new report should succeed (fresh month)
        response = self.client.post(
            "/api/diagnostics/reports/",
            self._create_report_payload(),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
