import logging
import re
from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Invoice, Subscription, SubscriptionPlan

logger = logging.getLogger(__name__)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "slug",
            "price",
            "trial_days",
            "max_staff",
            "max_reports",
            "features",
            "display_order",
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            "id",
            "amount",
            "status",
            "payment_method",
            "due_date",
            "paid_at",
            "transaction_id",
            "notes",
            "created_at",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    days_remaining_trial = serializers.IntegerField(read_only=True)
    is_trial_expired = serializers.BooleanField(read_only=True)
    invoices = InvoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "status",
            "trial_start",
            "trial_end",
            "billing_date",
            "started_at",
            "cancelled_at",
            "days_remaining_trial",
            "is_trial_expired",
            "invoices",
        ]


class CenterRegistrationSerializer(serializers.Serializer):
    """Public center registration — creates center + admin + subscription."""

    # Center info
    center_name = serializers.CharField(max_length=255)
    domain = serializers.SlugField(max_length=100)
    address = serializers.CharField(
        max_length=500, required=False, default="", allow_blank=True
    )
    contact_number = serializers.CharField(
        max_length=20, required=False, default="", allow_blank=True
    )

    # Admin account
    admin_first_name = serializers.CharField(max_length=150)
    admin_last_name = serializers.CharField(max_length=150)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(min_length=8, write_only=True)
    admin_phone = serializers.CharField(
        max_length=20, required=False, default="", allow_blank=True
    )

    # Plan
    plan_slug = serializers.SlugField(default="trial")

    def validate_domain(self, value):
        from core.tenants.models import DiagnosticCenter

        reserved = {"api", "www", "lablink", "admin", "app", "mail", "ftp"}
        if value.lower() in reserved:
            raise serializers.ValidationError(
                "This domain is reserved. Please choose another."
            )
        if DiagnosticCenter.objects.filter(domain=value).exists():
            raise serializers.ValidationError(
                "This domain is already taken. Please choose another."
            )
        return value.lower()

    def validate_admin_email(self, value):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value

    def validate_admin_password(self, value):
        from django.contrib.auth.password_validation import validate_password

        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages)) from None
        return value

    def validate_admin_phone(self, value):
        if value and not re.match(r"^01[0-9]{9}$", value):
            raise serializers.ValidationError(
                "Enter a valid Bangladeshi phone number (e.g. 01712345678)."
            )
        return value

    def validate_contact_number(self, value):
        if value and not re.match(r"^01[0-9]{9}$", value):
            raise serializers.ValidationError(
                "Enter a valid Bangladeshi phone number (e.g. 01712345678)."
            )
        return value

    def validate_plan_slug(self, value):
        if not SubscriptionPlan.objects.filter(slug=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid plan selected.")
        return value

    def create(self, validated_data):
        from django.contrib.auth import get_user_model
        from django.utils import timezone

        from core.tenants.models import DiagnosticCenter, Permission, Role, Staff

        User = get_user_model()

        plan = SubscriptionPlan.objects.get(slug=validated_data["plan_slug"])

        # 1. Create center
        center = DiagnosticCenter.objects.create(
            name=validated_data["center_name"],
            domain=validated_data["domain"],
            address=validated_data.get("address", ""),
            contact_number=validated_data.get("contact_number", ""),
            is_active=True,
            allow_online_appointments=True,
        )

        # 2. Grant all available permissions to center
        all_permissions = Permission.objects.all()
        center.available_permissions.set(all_permissions)

        # 3. Create admin role with all permissions
        admin_role, _created = Role.objects.get_or_create(
            name="Admin",
            center=center,
            defaults={"is_system": True},
        )
        admin_role.permissions.set(all_permissions)

        # 4. Create receptionist role (basic)
        recep_role, _created = Role.objects.get_or_create(
            name="Receptionist",
            center=center,
            defaults={"is_system": True},
        )
        view_perms = Permission.objects.filter(
            codename__startswith="view_",
        )
        recep_role.permissions.set(view_perms)

        # 5. Create medical technologist role
        lab_role, _created = Role.objects.get_or_create(
            name="Medical Technologist",
            center=center,
            defaults={"is_system": True},
        )
        lab_perms = Permission.objects.filter(
            category__in=["Reports", "Test Orders", "Patients"],
        )
        lab_role.permissions.set(lab_perms)

        # 6. Create admin user
        username = f"{validated_data['domain']}_admin"
        admin_user = User.objects.create_user(
            username=username,
            email=validated_data["admin_email"],
            password=validated_data["admin_password"],
            first_name=validated_data["admin_first_name"],
            last_name=validated_data["admin_last_name"],
            phone_number=validated_data.get("admin_phone", ""),
            center=center,
        )

        # 7. Create staff record for admin
        Staff.objects.create(
            user=admin_user,
            center=center,
            role=admin_role,
        )

        # 8. Create subscription
        now = timezone.now()
        is_trial = validated_data["plan_slug"] == "trial"

        subscription = Subscription.objects.create(
            center=center,
            plan=plan,
            status=Subscription.Status.TRIAL
            if is_trial
            else Subscription.Status.ACTIVE,
            trial_start=now if is_trial else None,
            trial_end=(
                now + timezone.timedelta(days=plan.trial_days) if is_trial else None
            ),
            billing_date=(
                (now + timezone.timedelta(days=plan.trial_days)).date()
                if is_trial
                else date.today()
            ),
        )

        # 9. Create first invoice for paid plans
        if not is_trial:
            Invoice.objects.create(
                subscription=subscription,
                amount=plan.price,
                status=Invoice.Status.PENDING,
                due_date=date.today(),
            )

        logger.info(
            "Center registered: %s (domain=%s, plan=%s)",
            center.name,
            center.domain,
            plan.name,
        )

        return {
            "center": center,
            "admin_user": admin_user,
            "subscription": subscription,
        }
