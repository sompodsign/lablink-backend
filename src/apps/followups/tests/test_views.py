import logging
from datetime import date, timedelta

from rest_framework import status
from rest_framework.test import APITestCase

from apps.followups.models import FollowUp
from helpers.test_factories import (
    jwt_auth_header,
    make_center,
    make_doctor,
    make_patient,
    make_staff,
    make_user,
)

logger = logging.getLogger(__name__)


class FollowUpViewSetBase(APITestCase):
    """Shared setup for FollowUp view tests."""

    def setUp(self):
        # Clean any stale rows left by previous --keepdb runs
        FollowUp.objects.all().delete()

        self.center = make_center("Test Center FU", "test-center-fu")
        self.patient = make_patient("patient_fu1", self.center)

        # Doctor
        self.doctor_user = make_user("doctor_fu1", "Dr", "Smith", center=self.center)
        self.doctor = make_doctor(self.doctor_user, self.center)

        # Receptionist (staff)
        self.staff_user = make_user("staff_fu1", "Nurse", "Mary", center=self.center)
        make_staff(self.staff_user, self.center, role_name="Receptionist")

        self.url = "/api/followups/"

    def _auth(self, user):
        self.client.credentials(**jwt_auth_header(user))
        self.client.defaults["SERVER_NAME"] = f"{self.center.domain}.localhost"

    def _create_followup(
        self, doctor=None, patient=None, days_ahead=7, fu_status=None, **kwargs
    ):
        fu = FollowUp.objects.create(
            center=self.center,
            patient=patient or self.patient,
            doctor=doctor,
            scheduled_date=date.today() + timedelta(days=days_ahead),
            reason="Test reason",
            created_by=self.staff_user,
            updated_by=self.staff_user,
            **({"status": fu_status} if fu_status else {}),
            **kwargs,
        )
        return fu

    def _results(self, response):
        """Extract records from paginated response."""
        return response.data.get("results", response.data)


class FollowUpCreateTest(FollowUpViewSetBase):
    def test_doctor_can_create_followup(self):
        self._auth(self.doctor_user)
        payload = {
            "patient": self.patient.pk,
            "scheduled_date": str(date.today() + timedelta(days=14)),
            "reason": "CBC recheck",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(
            FollowUp.objects.filter(center=self.center, reason="CBC recheck").exists()
        )

    def test_staff_can_create_followup(self):
        self._auth(self.staff_user)
        payload = {
            "patient": self.patient.pk,
            "scheduled_date": str(date.today() + timedelta(days=14)),
            "reason": "Blood sugar recheck",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_unauthenticated_cannot_create(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class FollowUpListTest(FollowUpViewSetBase):
    def test_staff_sees_all_followups(self):
        self._create_followup(doctor=self.doctor)
        self._auth(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._results(response)
        self.assertGreaterEqual(len(results), 1)

    def test_doctor_sees_only_own_followups(self):
        self._create_followup(doctor=self.doctor)  # doctor's own
        self._create_followup(doctor=None)  # unassigned — not doctor's
        self._auth(self.doctor_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._results(response)
        # Doctor without manage_followups sees only their assigned follow-up
        self.assertEqual(len(results), 1)

    def test_filter_by_status(self):
        self._create_followup(fu_status=FollowUp.STATUS_COMPLETED)
        self._create_followup(fu_status=FollowUp.STATUS_PENDING)
        self._auth(self.staff_user)
        response = self.client.get(self.url + "?status=COMPLETED")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "COMPLETED")

    def test_filter_overdue(self):
        self._create_followup(days_ahead=-2)  # overdue (past)
        self._create_followup(days_ahead=7)  # future, not overdue
        self._auth(self.staff_user)
        response = self.client.get(self.url + "?overdue=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._results(response)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["is_overdue"])


class FollowUpUpdateTest(FollowUpViewSetBase):
    def test_staff_can_update_pending_followup(self):
        fu = self._create_followup()
        self._auth(self.staff_user)
        new_date = str(date.today() + timedelta(days=21))
        response = self.client.patch(
            f"{self.url}{fu.pk}/", {"scheduled_date": new_date}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_cannot_update_completed_followup(self):
        fu = self._create_followup(fu_status=FollowUp.STATUS_COMPLETED)
        self._auth(self.staff_user)
        response = self.client.patch(
            f"{self.url}{fu.pk}/", {"reason": "changed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FollowUpCompleteTest(FollowUpViewSetBase):
    def test_complete_pending_followup(self):
        fu = self._create_followup()
        self._auth(self.staff_user)
        response = self.client.post(f"{self.url}{fu.pk}/complete/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        fu.refresh_from_db()
        self.assertEqual(fu.status, FollowUp.STATUS_COMPLETED)
        self.assertIsNotNone(fu.completed_at)

    def test_cannot_complete_already_completed(self):
        fu = self._create_followup(fu_status=FollowUp.STATUS_COMPLETED)
        self._auth(self.staff_user)
        response = self.client.post(f"{self.url}{fu.pk}/complete/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FollowUpCancelTest(FollowUpViewSetBase):
    def test_cancel_pending_followup(self):
        fu = self._create_followup()
        self._auth(self.staff_user)
        response = self.client.post(
            f"{self.url}{fu.pk}/cancel/",
            {"cancel_reason": "Patient requested cancellation"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        fu.refresh_from_db()
        self.assertEqual(fu.status, FollowUp.STATUS_CANCELLED)
        self.assertEqual(fu.cancel_reason, "Patient requested cancellation")

    def test_cancel_requires_reason(self):
        fu = self._create_followup()
        self._auth(self.staff_user)
        response = self.client.post(f"{self.url}{fu.pk}/cancel/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_cancel_already_cancelled(self):
        fu = self._create_followup(
            fu_status=FollowUp.STATUS_CANCELLED, cancel_reason="Prior reason"
        )
        self._auth(self.staff_user)
        response = self.client.post(
            f"{self.url}{fu.pk}/cancel/",
            {"cancel_reason": "Again"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
