import logging
import secrets

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.notifications.emails import EmailType, send_email
from core.users.models import PatientProfile

from .models import DiagnosticCenter, Doctor, Permission, Staff

User = get_user_model()
logger = logging.getLogger(__name__)


class SuperadminStatsSerializer(serializers.Serializer):
    """Aggregate platform stats for the superadmin overview."""

    total_centers = serializers.IntegerField()
    active_centers = serializers.IntegerField()
    inactive_centers = serializers.IntegerField()
    total_users = serializers.IntegerField()
    total_patients = serializers.IntegerField()
    total_staff = serializers.IntegerField()
    total_doctors = serializers.IntegerField()
    total_appointments = serializers.IntegerField()
    total_test_orders = serializers.IntegerField()
    total_reports = serializers.IntegerField()


class SuperadminCenterSerializer(serializers.ModelSerializer):
    """Center with counts and active status."""

    staff_count = serializers.IntegerField(read_only=True)
    doctor_count = serializers.IntegerField(read_only=True)
    patient_count = serializers.IntegerField(read_only=True)
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = DiagnosticCenter
        fields = [
            "id",
            "name",
            "domain",
            "tagline",
            "address",
            "contact_number",
            "email",
            "logo_url",
            "primary_color",
            "opening_hours",
            "is_active",
            "staff_count",
            "doctor_count",
            "patient_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None


class SuperadminCenterDetailSerializer(SuperadminCenterSerializer):
    """Extended center serializer for detail/edit views."""

    logo = serializers.ImageField(required=False, allow_null=True)

    class Meta(SuperadminCenterSerializer.Meta):
        fields = SuperadminCenterSerializer.Meta.fields + [
            "logo",
            "years_of_experience",
            "happy_patients_count",
            "test_types_available_count",
            "lab_support_availability",
        ]


class SuperadminCenterCreateSerializer(serializers.ModelSerializer):
    """Create a new diagnostic center with admin user auto-creation."""

    admin_email = serializers.EmailField(
        help_text="Email for the auto-created admin user. Credentials will be sent here.",
    )

    class Meta:
        model = DiagnosticCenter
        fields = [
            "name",
            "domain",
            "address",
            "contact_number",
            "email",
            "logo",
            "tagline",
            "primary_color",
            "opening_hours",
            "years_of_experience",
            "happy_patients_count",
            "test_types_available_count",
            "lab_support_availability",
            "admin_email",
        ]

    def validate_domain(self, value):
        if DiagnosticCenter.objects.filter(domain=value).exists():
            raise serializers.ValidationError(
                "A center with this domain already exists.",
            )
        return value

    def validate_admin_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists.",
            )
        return value

    def create(self, validated_data):
        from datetime import timedelta

        from django.utils import timezone

        from apps.subscriptions.models import Subscription, SubscriptionPlan

        from .models import Role

        admin_email = validated_data.pop("admin_email")

        with transaction.atomic():
            center = super().create(validated_data)
            # Grant all existing permissions to the new center
            all_permissions = Permission.objects.all()
            center.available_permissions.set(all_permissions)

            # ── Create default roles ──────────────────────────────
            admin_role, _ = Role.objects.get_or_create(
                name="Admin",
                center=center,
                defaults={"is_system": True},
            )
            admin_role.permissions.set(all_permissions)

            recep_role, _ = Role.objects.get_or_create(
                name="Receptionist",
                center=center,
                defaults={"is_system": True},
            )
            recep_role.permissions.set(
                Permission.objects.filter(codename__startswith="view_"),
            )

            lab_role, _ = Role.objects.get_or_create(
                name="Medical Technologist",
                center=center,
                defaults={"is_system": True},
            )
            lab_role.permissions.set(
                Permission.objects.filter(
                    category__in=["Reports", "Test Orders", "Patients"],
                ),
            )

            assistant_role, _ = Role.objects.get_or_create(
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

            # ── Create admin user ─────────────────────────────────
            username = f"{center.domain}_admin"
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{center.domain}_admin_{counter}"
                counter += 1

            password = secrets.token_urlsafe(10)
            admin_user = User.objects.create_user(
                username=username,
                email=admin_email,
                password=password,
                first_name="Admin",
                last_name=center.name,
                center=center,
                is_active=True,
            )

            Staff.objects.create(
                user=admin_user,
                center=center,
                role=admin_role,
            )

            # ── Auto-create trial subscription ────────────────────
            trial_plan = SubscriptionPlan.objects.filter(slug="trial").first()
            if trial_plan:
                now = timezone.now()
                Subscription.objects.create(
                    center=center,
                    plan=trial_plan,
                    status=Subscription.Status.TRIAL,
                    trial_start=now,
                    trial_end=now + timedelta(days=trial_plan.trial_days),
                    billing_date=(now + timedelta(days=trial_plan.trial_days)).date(),
                )

        # Send credentials email (outside transaction)
        send_email(
            EmailType.STAFF_CREDENTIALS,
            recipient=admin_email,
            context={
                "first_name": admin_user.first_name,
                "role_name": "Admin",
                "center_name": center.name,
                "username": username,
                "password": password,
            },
        )

        # Also send center welcome email
        if center.email:
            send_email(
                EmailType.CENTER_CREATED,
                recipient=center.email,
                context={"center_name": center.name},
            )

        logger.info(
            "Center %s created with admin user %s",
            center.name,
            username,
        )

        return center


class SuperadminUserSerializer(serializers.ModelSerializer):
    """User with center and role info for cross-tenant listing."""

    center_name = serializers.SerializerMethodField()
    center_id = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "is_active",
            "is_superuser",
            "approval_status",
            "date_joined",
            "center_name",
            "center_id",
            "role_name",
            "user_type",
        ]
        read_only_fields = [
            "id",
            "username",
            "date_joined",
            "center_name",
            "center_id",
            "role_name",
            "user_type",
        ]

    def get_center_name(self, obj):
        if obj.center:
            return obj.center.name
        return None

    def get_center_id(self, obj):
        return obj.center_id

    def get_role_name(self, obj):
        if obj.is_superuser:
            return "Superadmin"
        if hasattr(obj, "staff_profile"):
            return obj.staff_profile.role.name
        if hasattr(obj, "doctor_profile"):
            return "Doctor"
        if hasattr(obj, "patient_profile"):
            return "Patient"
        return "Unassigned"

    def get_user_type(self, obj):
        if obj.is_superuser:
            return "superadmin"
        if hasattr(obj, "staff_profile"):
            return "staff"
        if hasattr(obj, "doctor_profile"):
            return "doctor"
        if hasattr(obj, "patient_profile"):
            return "patient"
        return "unassigned"


class SuperadminStaffSerializer(serializers.ModelSerializer):
    """Staff with user info and center name."""

    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.CharField(
        source="user.get_full_name",
        read_only=True,
    )
    email = serializers.EmailField(source="user.email", read_only=True)
    center_name = serializers.CharField(
        source="center.name",
        read_only=True,
    )
    role_name = serializers.CharField(source="role.name", read_only=True)
    is_active = serializers.BooleanField(
        source="user.is_active",
        read_only=True,
    )

    class Meta:
        model = Staff
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "center_name",
            "role_name",
            "is_active",
        ]


class SuperadminStaffCreateSerializer(serializers.Serializer):
    """Superadmin creates a user + staff record at any center."""

    center_id = serializers.PrimaryKeyRelatedField(
        queryset=DiagnosticCenter.objects.all(),
        source="center",
    )
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        default="",
    )
    role_id = serializers.IntegerField()

    def validate_center_id(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "Cannot add staff to an inactive center.",
            )
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists.",
            )
        return value

    def validate(self, data):
        from apps.subscriptions.models import Subscription

        from .models import Role

        center = data["center"]
        role_id = data.get("role_id")
        try:
            role = Role.objects.get(pk=role_id, center=center)
        except Role.DoesNotExist:
            raise serializers.ValidationError(
                {"role_id": "Role does not belong to this center."},
            ) from None
        data["role"] = role

        # Enforce max_staff limit
        try:
            sub = (
                Subscription.objects.select_related("plan")
                .filter(
                    center=center,
                )
                .latest("started_at")
            )
            max_staff = sub.plan.max_staff
        except Subscription.DoesNotExist:
            max_staff = -1

        if max_staff != -1:
            current_count = Staff.objects.filter(center=center).count()
            if current_count >= max_staff:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            f"Staff limit reached ({current_count}/{max_staff}). "
                            f"Upgrade the plan to add more staff members."
                        ]
                    }
                )

        return data

    def create(self, validated_data):
        center = validated_data["center"]
        role = validated_data["role"]

        with transaction.atomic():
            base_username = (
                f"{validated_data['first_name'].lower()}"
                f"_{validated_data['last_name'].lower()}"
            )
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            password = secrets.token_urlsafe(10)
            self._generated_password = password
            user = User.objects.create_user(
                username=username,
                email=validated_data["email"],
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                phone_number=validated_data.get("phone_number", ""),
                password=password,
                center=center,
                is_active=True,
            )

            staff = Staff.objects.create(
                user=user,
                center=center,
                role=role,
            )

        # Send credentials email (outside transaction)
        if user.email:
            send_email(
                EmailType.STAFF_CREDENTIALS,
                recipient=user.email,
                context={
                    "first_name": user.first_name,
                    "role_name": role.name,
                    "center_name": center.name,
                    "username": username,
                    "password": password,
                },
            )

        return staff


class SuperadminDoctorCreateSerializer(serializers.Serializer):
    """Superadmin creates a user + doctor record at any center."""

    center_id = serializers.PrimaryKeyRelatedField(
        queryset=DiagnosticCenter.objects.all(),
        source="center",
    )
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        default="",
    )
    phone_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        default="",
    )
    specialization = serializers.CharField(max_length=255)
    designation = serializers.CharField(max_length=255)
    bio = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_center_id(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "Cannot add doctor to an inactive center.",
            )
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists.",
            )
        return value

    def create(self, validated_data):
        center = validated_data["center"]

        with transaction.atomic():
            base_username = (
                f"dr_{validated_data['first_name'].lower()}"
                f"_{validated_data['last_name'].lower()}"
            )
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=validated_data.get("email", ""),
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                phone_number=validated_data.get("phone_number", ""),
                center=center,
            )

            doctor = Doctor.objects.create(
                user=user,
                specialization=validated_data["specialization"],
                designation=validated_data["designation"],
                bio=validated_data.get("bio", ""),
            )

        return doctor


class SuperadminDoctorSerializer(serializers.ModelSerializer):
    """Doctor with user info and center."""

    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.CharField(
        source="user.get_full_name",
        read_only=True,
    )
    email = serializers.EmailField(source="user.email", read_only=True)
    center_name = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(
        source="user.is_active",
        read_only=True,
    )

    class Meta:
        model = Doctor
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "specialization",
            "designation",
            "center_name",
            "is_active",
        ]

    def get_center_name(self, obj):
        center = obj.user.center
        return center.name if center else None


class SuperadminPatientSerializer(serializers.ModelSerializer):
    """Patient with user info and registered center."""

    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.CharField(
        source="user.get_full_name",
        read_only=True,
    )
    email = serializers.EmailField(source="user.email", read_only=True)
    center_name = serializers.SerializerMethodField()

    class Meta:
        model = PatientProfile
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "phone_number",
            "date_of_birth",
            "gender",
            "blood_group",
            "center_name",
            "created_at",
        ]

    def get_center_name(self, obj):
        if obj.registered_at_center:
            return obj.registered_at_center.name
        return None
