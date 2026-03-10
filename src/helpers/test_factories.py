"""Shared test factory helpers for LabLink backend tests."""

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.appointments.models import Appointment
from apps.diagnostics.models import (
    CenterTestPricing,
    Report,
    ReportTemplate,
    TestOrder,
    TestType,
)
from core.tenants.models import DiagnosticCenter, Doctor, Staff
from core.users.models import PatientProfile

User = get_user_model()


# ── Object Factories ──────────────────────────────────────────────


def make_center(name="Center A", domain="center-a", **kwargs):
    defaults = {
        "address": "123 Test St",
        "contact_number": "01700000001",
    }
    defaults.update(kwargs)
    return DiagnosticCenter.objects.create(name=name, domain=domain, **defaults)


def make_user(username, first_name="Test", last_name="User", phone="", **kwargs):
    return User.objects.create_user(
        username=username,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone,
        password="testpass123",
        **kwargs,
    )


def make_staff(user, center, role=Staff.Role.RECEPTIONIST):
    return Staff.objects.create(user=user, center=center, role=role)


def make_doctor(user, *centers):
    doctor = Doctor.objects.create(
        user=user,
        specialization="General",
        designation="MD",
    )
    for c in centers:
        doctor.centers.add(c)
    return doctor


def make_patient(username, center, **profile_kwargs):
    user = make_user(username, "Pat", "Ient")
    PatientProfile.objects.create(
        user=user,
        registered_at_center=center,
        **profile_kwargs,
    )
    return user


def make_appointment(patient, center, doctor=None, **kwargs):
    defaults = {"date": "2026-03-10", "time": "10:00"}
    defaults.update(kwargs)
    return Appointment.objects.create(
        patient=patient,
        center=center,
        doctor=doctor,
        **defaults,
    )


def make_test_type(name="CBC", price="500.00"):
    return TestType.objects.create(
        name=name,
        description="Blood test",
        base_price=price,
    )


def make_pricing(center, test_type, price="500.00", is_available=True):
    return CenterTestPricing.objects.create(
        center=center,
        test_type=test_type,
        price=price,
        is_available=is_available,
    )


def make_test_order(patient, center, test_type, created_by=None, **kwargs):
    defaults = {
        "status": TestOrder.Status.PENDING,
        "priority": TestOrder.Priority.NORMAL,
    }
    defaults.update(kwargs)
    return TestOrder.objects.create(
        patient=patient,
        center=center,
        test_type=test_type,
        created_by=created_by,
        **defaults,
    )


def make_report(test_order, test_type, **kwargs):
    defaults = {
        "result_text": "Normal results",
        "status": Report.Status.DRAFT,
    }
    defaults.update(kwargs)
    return Report.objects.create(
        test_order=test_order,
        test_type=test_type,
        **defaults,
    )


def make_report_template(test_type, center, fields=None):
    if fields is None:
        fields = [
            {"name": "Hemoglobin", "unit": "g/dL", "ref_range": "13.5-17.5"},
        ]
    return ReportTemplate.objects.create(
        test_type=test_type, center=center, fields=fields,
    )


# ── Auth Helpers ──────────────────────────────────────────────────


def jwt_auth_header(user):
    token = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


class FakeRequest:
    """Minimal request-like object for permission testing."""

    def __init__(self, user, tenant):
        self.user = user
        self.tenant = tenant
