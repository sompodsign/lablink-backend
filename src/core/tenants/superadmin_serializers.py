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
    """Create a new diagnostic center with all core + design fields."""

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
        ]

    def validate_domain(self, value):
        if DiagnosticCenter.objects.filter(domain=value).exists():
            raise serializers.ValidationError(
                "A center with this domain already exists.",
            )
        return value

    def create(self, validated_data):
        center = super().create(validated_data)
        # Grant all existing permissions to the new center
        center.available_permissions.set(Permission.objects.all())

        # Send welcome email to newly created center
        if center.email:
            send_email(
                EmailType.CENTER_CREATED,
                recipient=center.email,
                context={'center_name': center.name},
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
                    'first_name': user.first_name,
                    'role_name': role.name,
                    'center_name': center.name,
                    'username': username,
                    'password': password,
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
