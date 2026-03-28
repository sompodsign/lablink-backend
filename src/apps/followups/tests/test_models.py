import logging
from datetime import date, timedelta

from django.test import SimpleTestCase

from apps.followups.models import FollowUp

logger = logging.getLogger(__name__)


def _make_unsaved_followup(**kwargs) -> FollowUp:
    """
    Build an unsaved, unpersisted FollowUp for pure property testing.
    We bypass __init__ entirely to avoid FK validation.
    """
    fu = object.__new__(FollowUp)
    # Set only the fields the properties care about
    fu.status = kwargs.get("status", FollowUp.STATUS_PENDING)
    fu.scheduled_date = kwargs.get("scheduled_date", date.today())
    return fu


class FollowUpIsOverdueTest(SimpleTestCase):
    """Unit tests for FollowUp.is_overdue property — no DB required."""

    def test_is_overdue_false_for_future_date(self):
        fu = _make_unsaved_followup(scheduled_date=date.today() + timedelta(days=7))
        self.assertFalse(fu.is_overdue)

    def test_is_overdue_false_for_today(self):
        fu = _make_unsaved_followup(scheduled_date=date.today())
        self.assertFalse(fu.is_overdue)

    def test_is_overdue_true_for_past_pending(self):
        fu = _make_unsaved_followup(scheduled_date=date.today() - timedelta(days=1))
        self.assertTrue(fu.is_overdue)

    def test_is_overdue_false_for_completed_past(self):
        fu = _make_unsaved_followup(
            status=FollowUp.STATUS_COMPLETED,
            scheduled_date=date.today() - timedelta(days=1),
        )
        self.assertFalse(fu.is_overdue)

    def test_is_overdue_false_for_cancelled_past(self):
        fu = _make_unsaved_followup(
            status=FollowUp.STATUS_CANCELLED,
            scheduled_date=date.today() - timedelta(days=1),
        )
        self.assertFalse(fu.is_overdue)


class FollowUpIsResolvedTest(SimpleTestCase):
    """Unit tests for FollowUp.is_resolved property — no DB required."""

    def test_is_resolved_false_for_pending(self):
        fu = _make_unsaved_followup(status=FollowUp.STATUS_PENDING)
        self.assertFalse(fu.is_resolved)

    def test_is_resolved_true_for_completed(self):
        fu = _make_unsaved_followup(status=FollowUp.STATUS_COMPLETED)
        self.assertTrue(fu.is_resolved)

    def test_is_resolved_true_for_cancelled(self):
        fu = _make_unsaved_followup(status=FollowUp.STATUS_CANCELLED)
        self.assertTrue(fu.is_resolved)


class FollowUpStatusConstantsTest(SimpleTestCase):
    """Verify status constant values match expected strings."""

    def test_status_values(self):
        self.assertEqual(FollowUp.STATUS_PENDING, "PENDING")
        self.assertEqual(FollowUp.STATUS_COMPLETED, "COMPLETED")
        self.assertEqual(FollowUp.STATUS_CANCELLED, "CANCELLED")
