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
from apps.payments.models import Invoice, InvoiceItem
from apps.subscriptions.models import Subscription, SubscriptionPlan
from core.tenants.models import DiagnosticCenter, Doctor, Permission, Role, Staff
from core.users.models import PatientProfile

User = get_user_model()

# ── Default permission sets ───────────────────────────────────────

ALL_PERMISSIONS = None  # sentinel — means "all available permissions"

ADMIN_PERMISSIONS = ALL_PERMISSIONS

LAB_TECH_PERMISSIONS = [
    "view_patients",
    "view_reports",
    "create_reports",
    "manage_reports",
    "view_test_orders",
    "manage_test_orders",
]

RECEPTIONIST_PERMISSIONS = [
    "view_patients",
    "manage_patients",
    "view_appointments",
    "manage_appointments",
    "view_reports",
    "view_payments",
    "manage_payments",
]

DOCTOR_PERMISSIONS = [
    "view_patients",
    "view_appointments",
    "manage_appointments",
    "view_test_orders",
    "view_reports",
    "create_reports",
]


# ── Object Factories ──────────────────────────────────────────────


def _get_or_create_default_plan():
    """Return the default test subscription plan, creating if needed."""
    plan, _created = SubscriptionPlan.objects.get_or_create(
        slug="test-plan",
        defaults={
            "name": "Test Plan",
            "price": "0.00",
            "trial_days": 0,
            "max_staff": -1,
            "max_reports": -1,
        },
    )
    return plan


def make_subscription(center, status="ACTIVE", plan=None):
    """Create an active subscription for the center."""
    if plan is None:
        plan = _get_or_create_default_plan()
    return Subscription.objects.create(
        center=center,
        plan=plan,
        status=status,
    )


def make_center(name="Center A", domain="center-a", **kwargs):
    defaults = {
        "address": "123 Test St",
        "contact_number": "01700000001",
    }
    defaults.update(kwargs)
    center = DiagnosticCenter.objects.create(name=name, domain=domain, **defaults)
    make_subscription(center)
    return center


def make_user(username, first_name="Test", last_name="User", phone="", **kwargs):
    return User.objects.create_user(
        username=username,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone,
        password="testpass123",
        **kwargs,
    )


def _get_or_create_role(center, role_name, permissions=None):
    """Get or create a Role for the given center with specified permissions."""
    role, created = Role.objects.get_or_create(
        name=role_name,
        center=center,
        defaults={
            "is_system": role_name
            in ("Admin", "Medical Technologist", "Receptionist", "Medical Assistant")
        },
    )
    if created or permissions is not None:
        if permissions is ALL_PERMISSIONS:
            role.permissions.set(Permission.objects.all())
        elif permissions is not None:
            perm_objs = Permission.objects.filter(codename__in=permissions)
            role.permissions.set(perm_objs)
    return role


def make_staff(user, center, role_name="Receptionist", permissions=None, role=None):
    """Create a staff member with a named role.

    Args:
        user: The User instance.
        center: The DiagnosticCenter instance.
        role_name: Human-readable role name (e.g. 'Admin', 'Medical Technologist').
        permissions: List of permission codenames, or None for default.
            Use ALL_PERMISSIONS sentinel for all permissions.
    """
    # Support `role=` kwarg as alias for `role_name=`
    if role is not None:
        role_name = role
    # Map legacy Staff.Role values to new names
    role_name_map = {
        "ADMIN": "Admin",
        "LAB_TECHNICIAN": "Medical Technologist",
        "MEDICAL_TECHNOLOGIST": "Medical Technologist",
        "RECEPTIONIST": "Receptionist",
    }
    role_name = role_name_map.get(role_name, role_name)

    if permissions is None:
        perm_map = {
            "Admin": ALL_PERMISSIONS,
            "Medical Technologist": LAB_TECH_PERMISSIONS,
            "Receptionist": RECEPTIONIST_PERMISSIONS,
            "Doctor": DOCTOR_PERMISSIONS,
        }
        permissions = perm_map.get(role_name, [])

    role = _get_or_create_role(center, role_name, permissions)

    # Ensure user.center matches staff.center
    if user.center_id != center.id:
        user.center = center
        user.save(update_fields=["center_id"])

    return Staff.objects.create(user=user, center=center, role=role)


def make_doctor(user, center=None):
    # Set user.center if center provided
    if center and user.center_id != center.id:
        user.center = center
        user.save(update_fields=["center_id"])

    doctor = Doctor.objects.create(
        user=user,
        specialization="General",
        designation="MD",
    )
    return doctor


def make_patient(username, center, **profile_kwargs):
    user = make_user(username, "Pat", "Ient", center=center)
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
        test_type=test_type,
        center=center,
        fields=fields,
    )


def make_invoice(patient, center, created_by=None, **kwargs):
    defaults = {
        "status": Invoice.Status.ISSUED,
    }
    defaults.update(kwargs)
    return Invoice.objects.create(
        patient=patient,
        center=center,
        created_by=created_by,
        **defaults,
    )


def make_invoice_item(invoice, **kwargs):
    defaults = {
        "item_type": InvoiceItem.ItemType.TEST,
        "description": "CBC Test",
        "quantity": 1,
        "unit_price": "500.00",
    }
    defaults.update(kwargs)
    return InvoiceItem.objects.create(
        invoice=invoice,
        **defaults,
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
