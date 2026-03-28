import logging

from django.test import SimpleTestCase

from core.tenants.permissions import (
    IsCenterStaff,
    IsCenterStaffOrDoctor,
)
from helpers.test_factories import FakeRequest

logger = logging.getLogger(__name__)


class PermissionUnitTest(SimpleTestCase):
    """Unit tests for permission class behavior (no DB needed)."""

    def _fake_user(self, has_staff=False, has_doctor=False, is_auth=True):
        from unittest.mock import MagicMock

        user = MagicMock()
        user.is_authenticated = is_auth
        if has_staff:
            user.staff_profile.center_id = 1
        else:
            del user.staff_profile
        if has_doctor:
            user.doctor_profile = MagicMock()
            user.center_id = 1
        else:
            del user.doctor_profile
        return user

    def _fake_tenant(self, center_id=1):
        from unittest.mock import MagicMock

        t = MagicMock()
        t.id = center_id
        return t

    def _fake_request(self, user, tenant=None):
        req = FakeRequest(user=user, tenant=tenant or self._fake_tenant())
        return req

    def test_unauthenticated_denied_by_staff(self):
        user = self._fake_user(is_auth=False)
        perm = IsCenterStaff()
        req = self._fake_request(user)
        self.assertFalse(perm.has_permission(req, None))

    def test_center_staff_allowed(self):
        user = self._fake_user(has_staff=True)
        perm = IsCenterStaff()
        req = self._fake_request(user)
        self.assertTrue(perm.has_permission(req, None))

    def test_center_doctor_allowed_by_staffordoctor(self):
        user = self._fake_user(has_doctor=True)
        perm = IsCenterStaffOrDoctor()
        req = self._fake_request(user)
        self.assertTrue(perm.has_permission(req, None))

    def test_no_tenant_denied(self):
        user = self._fake_user(has_staff=True)
        perm = IsCenterStaff()
        req = FakeRequest(user=user, tenant=None)
        self.assertFalse(perm.has_permission(req, None))
