import logging
import re
from datetime import date, timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
    PUBLIC_PLAN_SLUGS,
    Invoice,
    PaymentInfo,
    PaymentSubmission,
    Subscription,
    SubscriptionPlan,
)

logger = logging.getLogger(__name__)


class PaymentInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentInfo
        fields = ["id", "method", "label", "details", "icon"]


class PaymentSubmissionSerializer(serializers.ModelSerializer):
    payment_method_label = serializers.CharField(
        source="payment_method.label",
        read_only=True,
    )
    submitted_by_name = serializers.SerializerMethodField()
    invoice_amount = serializers.DecimalField(
        source="invoice.amount",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    center_name = serializers.CharField(
        source="invoice.subscription.center.name",
        read_only=True,
    )

    class Meta:
        model = PaymentSubmission
        fields = [
            "id",
            "invoice",
            "invoice_amount",
            "center_name",
            "payment_method",
            "payment_method_label",
            "transaction_id",
            "submitted_by",
            "submitted_by_name",
            "status",
            "admin_notes",
            "submitted_at",
            "reviewed_at",
        ]
        read_only_fields = [
            "id",
            "submitted_by",
            "status",
            "admin_notes",
            "submitted_at",
            "reviewed_at",
        ]

    def get_submitted_by_name(self, obj):
        if obj.submitted_by:
            return (
                f"{obj.submitted_by.first_name} {obj.submitted_by.last_name}"
            ).strip() or obj.submitted_by.username
        return None


class SubmitPaymentSerializer(serializers.Serializer):
    """Center admin: submit payment proof for an invoice."""

    payment_method_id = serializers.IntegerField()
    transaction_id = serializers.CharField(max_length=100)


class SubmitPaymentResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    submission = PaymentSubmissionSerializer()


class UpdatePaymentSubmissionResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    submission = PaymentSubmissionSerializer()


class ChangePlanRequestSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()


class ChangePlanResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    require_payment = serializers.BooleanField()
    invoice_id = serializers.IntegerField(required=False, allow_null=True)


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
            "monthly_ai_credits",
            "features",
            "display_order",
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    subscription_status = serializers.CharField(
        source='subscription.status',
        read_only=True,
    )
    target_plan_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id',
            'amount',
            'original_amount',
            'credit_applied',
            'status',
            'payment_method',
            'due_date',
            'paid_at',
            'transaction_id',
            'notes',
            'created_at',
            'subscription_status',
            'target_plan_id',
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    days_remaining_trial = serializers.IntegerField(read_only=True)
    is_trial_expired = serializers.BooleanField(read_only=True)
    invoices = InvoiceSerializer(many=True, read_only=True)
    current_report_count = serializers.SerializerMethodField()
    has_used_trial = serializers.BooleanField(read_only=True)
    credit_balance = serializers.DecimalField(
        source="center.credit_balance", max_digits=10, decimal_places=0, read_only=True
    )

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
            "cancel_at_period_end",
            "days_remaining_trial",
            "is_trial_expired",
            "available_ai_credits",
            "credit_balance",
            "invoices",
            "current_report_count",
            "has_used_trial",
        ]

    def get_current_report_count(self, obj):
        from django.utils import timezone as tz

        from apps.diagnostics.models import Report

        now = tz.now()
        return Report.objects.filter(
            test_order__center=obj.center,
            created_at__year=now.year,
            created_at__month=now.month,
            is_deleted=False,
        ).count()

    def get_has_used_trial(self, obj):
        return getattr(obj.center, "has_used_trial", False)


class SuperadminChangePlanResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    subscription = SubscriptionSerializer()


class SuperadminSubscriptionSerializer(serializers.ModelSerializer):
    """Superadmin: create / update subscriptions for any center."""

    center_id = serializers.IntegerField()
    plan_id = serializers.IntegerField()
    center_name = serializers.CharField(source="center.name", read_only=True)
    center_domain = serializers.CharField(source="center.domain", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    credit_balance = serializers.DecimalField(
        source="center.credit_balance", max_digits=10, decimal_places=0, read_only=True
    )

    class Meta:
        model = Subscription
        fields = [
            "id",
            "center_id",
            "center_name",
            "center_domain",
            "plan_id",
            "plan_name",
            "status",
            "trial_start",
            "trial_end",
            "billing_date",
            "started_at",
            "cancelled_at",
            "available_ai_credits",
            "credit_balance",
        ]
        read_only_fields = ["id", "started_at", "cancelled_at", "available_ai_credits"]

    def validate_center_id(self, value):
        from core.tenants.models import DiagnosticCenter

        if not DiagnosticCenter.objects.filter(id=value).exists():
            raise serializers.ValidationError("Center not found.")
        # On create, reject if subscription already exists
        if not self.instance and Subscription.objects.filter(center_id=value).exists():
            raise serializers.ValidationError("This center already has a subscription.")
        return value

    def validate_plan_id(self, value):
        if not SubscriptionPlan.objects.filter(id=value).exists():
            raise serializers.ValidationError("Plan not found.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        status_value = attrs.get(
            "status",
            self.instance.status if self.instance else Subscription.Status.TRIAL,
        )
        billing_date = attrs.get(
            "billing_date",
            self.instance.billing_date if self.instance else None,
        )

        if status_value == Subscription.Status.ACTIVE and billing_date is None:
            attrs["billing_date"] = timezone.localdate() + timedelta(days=30)

        return attrs

    def create(self, validated_data):
        plan = SubscriptionPlan.objects.get(id=validated_data["plan_id"])
        status = validated_data.get("status", Subscription.Status.TRIAL)

        # Auto-populate trial dates if status is TRIAL and not provided
        if status == Subscription.Status.TRIAL:
            now = timezone.now()
            validated_data.setdefault("trial_start", now)
            validated_data.setdefault(
                "trial_end", now + timedelta(days=plan.trial_days)
            )
        elif status == Subscription.Status.INACTIVE:
            validated_data.setdefault("billing_date", timezone.localdate())

        return super().create(validated_data)


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
        if not SubscriptionPlan.objects.filter(
            slug=value,
            is_active=True,
            slug__in=PUBLIC_PLAN_SLUGS,
        ).exists():
            raise serializers.ValidationError("Invalid plan selected.")
        return value

    def create(self, validated_data):
        from django.contrib.auth import get_user_model

        from core.tenants.models import DiagnosticCenter, Permission, Role, Staff

        User = get_user_model()

        with transaction.atomic():
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

            # 5b. Create medical assistant role
            assistant_role, _created = Role.objects.get_or_create(
                name="Medical Assistant",
                center=center,
                defaults={"is_system": True},
            )
            assistant_role.permissions.set(
                Permission.objects.filter(
                    codename__in=[
                        "view_patients",
                        "manage_patients",
                        "view_appointments",
                        "manage_appointments",
                        "view_reports",
                        "view_test_orders",
                        "view_payments",
                    ],
                ),
            )

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
            is_free_trial_plan = validated_data["plan_slug"] == "trial"
            is_paid_plan = plan.price > 0

            if is_free_trial_plan:
                subscription = Subscription.objects.create(
                    center=center,
                    plan=plan,
                    status=Subscription.Status.TRIAL,
                    trial_start=now,
                    trial_end=now + timezone.timedelta(days=plan.trial_days),
                    billing_date=(now + timezone.timedelta(days=plan.trial_days)).date(),
                )
            elif is_paid_plan and not center.has_used_trial:
                subscription = Subscription.objects.create(
                    center=center,
                    plan=plan,
                    status=Subscription.Status.TRIAL,
                    trial_start=now,
                    trial_end=now + timezone.timedelta(days=plan.trial_days),
                    billing_date=(now + timezone.timedelta(days=plan.trial_days)).date(),
                )
            else:
                subscription = Subscription.objects.create(
                    center=center,
                    plan=plan,
                    status=Subscription.Status.INACTIVE,
                    trial_start=None,
                    trial_end=None,
                    billing_date=date.today(),
                )
                Invoice.objects.create(
                    subscription=subscription,
                    amount=plan.price,
                    status=Invoice.Status.PENDING,
                    due_date=date.today(),
                )

            center.has_used_trial = True
            center.save(update_fields=["has_used_trial"])

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
