"""
Tests for verifying that Superadmin and Center Admin master toggles correctly
gate SMS and Email notifications.
"""

from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from apps.diagnostics.models import Report, TestOrder, TestType
from core.tenants.models import DiagnosticCenter
from core.users.models import User


class NotificationGatesTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a Diagnostic Center
        cls.center = DiagnosticCenter.objects.create(
            name="Test Center",
            domain="testcenter",
            can_use_sms=True,
            can_use_email=True,
            use_sms=True,
            use_email=True,
            sms_enabled=True,
            email_notifications_enabled=True,
        )

        # Create a Medical Technologist
        cls.technologist = User.objects.create_user(
            username="tech@test.com",
            email="tech@test.com",
            password="password123",
            first_name="Tech",
        )
        cls.center.users.add(cls.technologist)
        # Assuming there's a role or permission logic; simpler to mock permission or grant it
        # Wait, using standard DRF test client we might bypass some decorators or just need permissions.

        # Create a patient
        cls.patient = User.objects.create_user(
            username="patient@test.com",
            email="patient@test.com",
            password="pwd",
            first_name="John",
            phone_number="+1234567890",
        )

        # Create Test Type
        cls.test_type = TestType.objects.create(name="CBC", base_price="10.00")

    def setUp(self):
        # Need to ensure self.technologist has center permissions correctly or mock it
        # Actually it's easier to mock `IsCenterMedicalTechnologist` and `HasCenterPermission` if they get in the way,
        # but let's see if we can just grant the permissions via patching or role.
        # Alternatively, use a Superadmin user which bypasses permissions anyway.
        from helpers.test_factories import jwt_auth_header

        self.superadmin = User.objects.create_superuser(
            "super@admin.com", "super@admin.com", "pass"
        )
        from helpers.test_factories import make_staff

        make_staff(self.superadmin, self.center, role="Admin")

        self.auth = jwt_auth_header(self.superadmin)

    def _create_report(self):
        # Create order
        order = TestOrder.objects.create(
            center=self.center,
            patient=self.patient,
            test_type=self.test_type,
            status=TestOrder.Status.COMPLETED,
        )
        # Create report
        report = Report.objects.create(
            test_order=order,
            test_type=self.test_type,
            status=Report.Status.DRAFT,
            result_data={"some": "data"},
        )
        return report

    @patch(
        "core.tenants.permissions.HasCenterPermission.has_permission", return_value=True
    )
    @patch("apps.diagnostics.services.notifications.send_report_ready_sms")
    @patch("apps.diagnostics.services.notifications.send_report_ready_email")
    def test_notifications_sent_when_all_toggles_enabled(
        self, mock_email, mock_sms, mock_perm
    ):
        report = self._create_report()

        # Verify
        response = self.client.post(
            f"/api/diagnostics/reports/{report.pk}/verify/", **self.auth
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Asserts
        mock_sms.assert_called_once_with(report, self.patient.phone_number)
        mock_email.assert_called_once_with(report, self.patient.email)

    @patch(
        "core.tenants.permissions.HasCenterPermission.has_permission", return_value=True
    )
    @patch("apps.diagnostics.services.notifications.send_report_ready_sms")
    @patch("apps.diagnostics.services.notifications.send_report_ready_email")
    def test_notifications_NOT_sent_if_superadmin_disables_can_use(
        self, mock_email, mock_sms, mock_perm
    ):
        self.center.can_use_sms = False
        self.center.can_use_email = False
        self.center.save()

        report = self._create_report()
        response = self.client.post(
            f"/api/diagnostics/reports/{report.pk}/verify/", **self.auth
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_sms.assert_not_called()
        mock_email.assert_not_called()

    @patch(
        "core.tenants.permissions.HasCenterPermission.has_permission", return_value=True
    )
    @patch("apps.diagnostics.services.notifications.send_report_ready_sms")
    @patch("apps.diagnostics.services.notifications.send_report_ready_email")
    def test_notifications_NOT_sent_if_center_admin_disables_use(
        self, mock_email, mock_sms, mock_perm
    ):
        # Superadmin enabled, but center admin disabled master toggle
        self.center.can_use_sms = True
        self.center.use_sms = False
        self.center.can_use_email = True
        self.center.use_email = False
        self.center.save()

        report = self._create_report()
        response = self.client.post(
            f"/api/diagnostics/reports/{report.pk}/verify/", **self.auth
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_sms.assert_not_called()
        mock_email.assert_not_called()

    @patch(
        "core.tenants.permissions.HasCenterPermission.has_permission", return_value=True
    )
    @patch("apps.diagnostics.services.notifications.send_report_ready_sms")
    @patch("apps.diagnostics.services.notifications.send_report_ready_email")
    def test_notifications_NOT_sent_if_operational_toggles_disabled(
        self, mock_email, mock_sms, mock_perm
    ):
        # Masters enabled, but specific toggles disabled
        self.center.use_sms = True
        self.center.sms_enabled = False
        self.center.use_email = True
        self.center.email_notifications_enabled = False
        self.center.save()

        report = self._create_report()
        response = self.client.post(
            f"/api/diagnostics/reports/{report.pk}/verify/", **self.auth
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_sms.assert_not_called()
        mock_email.assert_not_called()

    def test_settings_serializer_forces_sub_toggles_off_when_superadmin_disables(self):
        from core.tenants.serializers import CenterSettingsSerializer

        self.center.can_use_sms = False
        self.center.can_use_email = False
        self.center.save()

        serializer = CenterSettingsSerializer(
            instance=self.center,
            data={
                "use_sms": True,
                "sms_enabled": True,
                "use_email": True,
                "email_notifications_enabled": True,
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid())
        validated = serializer.validated_data

        # Because superadmin disabled them, everything should be forced False
        self.assertFalse(validated.get("use_sms"))
        self.assertFalse(validated.get("sms_enabled"))
        self.assertFalse(validated.get("send_sms_invoice"))
        self.assertFalse(validated.get("use_email"))
        self.assertFalse(validated.get("email_notifications_enabled"))
        self.assertFalse(validated.get("send_email_invoice"))

    def test_settings_serializer_forces_sub_toggles_off_when_center_admin_disables(
        self,
    ):
        from core.tenants.serializers import CenterSettingsSerializer

        self.center.can_use_sms = True
        self.center.can_use_email = True
        self.center.save()

        serializer = CenterSettingsSerializer(
            instance=self.center,
            data={
                "use_sms": False,
                "sms_enabled": True,
                "use_email": False,
                "email_notifications_enabled": True,
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid())
        validated = serializer.validated_data

        # Validation should coerce operational toggles to False
        self.assertFalse(validated.get("sms_enabled"))
        self.assertFalse(validated.get("email_notifications_enabled"))
        self.assertFalse(validated.get("use_sms"))
        self.assertFalse(validated.get("use_email"))
