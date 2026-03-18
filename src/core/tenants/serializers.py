import logging
import secrets

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import serializers

from .models import DiagnosticCenter, Doctor, Permission, Role, Service, Staff

User = get_user_model()
logger = logging.getLogger(__name__)


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "title", "description", "icon", "order"]


class DiagnosticCenterSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()

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
            "years_of_experience",
            "happy_patients_count",
            "test_types_available_count",
            "lab_support_availability",
            "allow_online_appointments",
            "services",
        ]

    def get_logo_url(self, obj) -> str | None:
        if obj.logo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.logo.url)
        return None

    def get_services(self, obj) -> list:
        active_services = obj.services.filter(is_active=True)
        return ServiceSerializer(active_services, many=True).data


class CenterSettingsSerializer(serializers.ModelSerializer):
    """Admin-editable center settings."""

    logo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DiagnosticCenter
        fields = [
            "id",
            "name",
            "tagline",
            "address",
            "contact_number",
            "email",
            "logo",
            "logo_url",
            "primary_color",
            "opening_hours",
            "years_of_experience",
            "happy_patients_count",
            "test_types_available_count",
            "lab_support_availability",
            "allow_online_appointments",
        ]
        read_only_fields = ["id", "logo_url"]

    def get_logo_url(self, obj) -> str | None:
        if obj.logo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.logo.url)
        return None


class DoctorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.get_full_name")
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Doctor
        fields = ["id", "name", "email", "specialization", "designation", "bio"]


class DoctorManagementSerializer(serializers.ModelSerializer):
    """Full doctor management serializer for staff/admin use."""

    name = serializers.CharField(source="user.get_full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Doctor
        fields = [
            "id",
            "name",
            "email",
            "username",
            "specialization",
            "designation",
            "bio",
        ]
        read_only_fields = ["id", "name", "email", "username"]


class DoctorCreateSerializer(serializers.Serializer):
    """Creates a User + Doctor record and links to the tenant center."""

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    phone_number = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default=""
    )
    specialization = serializers.CharField(max_length=255)
    designation = serializers.CharField(max_length=255)
    bio = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_email(self, value):
        tenant = self.context["request"].tenant
        if value and User.objects.filter(email=value, center=tenant).exists():
            raise serializers.ValidationError(
                "A user with this email already exists at this center."
            )
        return value

    def create(self, validated_data):
        tenant = self.context["request"].tenant
        with transaction.atomic():
            username = f"dr_{validated_data['first_name'].lower()}_{validated_data['last_name'].lower()}"
            base_username = username
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
                center=tenant,
            )

            doctor = Doctor.objects.create(
                user=user,
                specialization=validated_data["specialization"],
                designation=validated_data["designation"],
                bio=validated_data.get("bio", ""),
            )

        return doctor


class DoctorActivitySerializer(serializers.Serializer):
    """
    Summary of a doctor's recent activity at the current center.
    Not bound to a single model — combines Appointments + TestOrders.
    """

    doctor = DoctorSerializer()
    total_appointments = serializers.IntegerField()
    total_test_orders = serializers.IntegerField()
    recent_appointments = serializers.ListField(child=serializers.DictField())


# ── Permission & Role Serializers ─────────────────────────────────


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "codename", "name", "category", "is_custom"]
        read_only_fields = ["id"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        write_only=True,
        source="permissions",
        required=False,
    )
    staff_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "permissions",
            "permission_ids",
            "is_system",
            "staff_count",
        ]
        read_only_fields = ["is_system"]

    def get_staff_count(self, obj) -> int:
        if obj.name == "Doctor":
            return Doctor.objects.filter(user__center=obj.center).count()
        return obj.staff_members.count()

    def create(self, validated_data):
        permissions = validated_data.pop("permissions", [])
        center = self.context["request"].tenant
        role = Role.objects.create(center=center, **validated_data)
        if permissions:
            role.permissions.set(permissions)
        return role

    def validate(self, data):
        """Ensure assigned permissions are within center's available set."""
        perms = data.get("permissions")
        if perms is not None:
            request = self.context.get("request")
            if request and hasattr(request, "tenant") and request.tenant:
                available_ids = set(
                    request.tenant.available_permissions.values_list(
                        "id",
                        flat=True,
                    )
                )
                invalid = [p.codename for p in perms if p.id not in available_ids]
                if invalid:
                    raise serializers.ValidationError(
                        {
                            "permission_ids": (
                                f"Permissions not available at this center: "
                                f"{', '.join(invalid)}"
                            )
                        }
                    )
        return data

    def update(self, instance, validated_data):
        permissions = validated_data.pop("permissions", None)
        instance.name = validated_data.get("name", instance.name)
        instance.save(update_fields=["name"])
        if permissions is not None:
            instance.permissions.set(permissions)
        return instance


# ── Staff Serializers ─────────────────────────────────────────────


class StaffSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    name = serializers.CharField(source="user.get_full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone_number = serializers.CharField(
        source="user.phone_number",
        read_only=True,
    )
    is_active = serializers.BooleanField(
        source="user.is_active",
        read_only=True,
    )
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source="role",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Staff
        fields = [
            "id",
            "user_id",
            "name",
            "email",
            "phone_number",
            "role",
            "role_name",
            "role_id",
            "is_active",
        ]
        read_only_fields = ["role"]


class StaffCreateSerializer(serializers.Serializer):
    """Create a new user and assign them as staff at the current center."""

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        default="",
    )
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
    )

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists.",
            )
        return value

    def validate_role_id(self, value):
        tenant = self.context["request"].tenant
        if value.center_id != tenant.id:
            raise serializers.ValidationError(
                "Role does not belong to this center.",
            )
        return value

    def create(self, validated_data):
        tenant = self.context["request"].tenant
        role = validated_data["role_id"]

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
                is_active=True,
            )

            staff = Staff.objects.create(
                user=user,
                center=tenant,
                role=role,
            )

        # Send credentials email (outside transaction)
        send_mail(
            subject=f"Welcome to {tenant.name} — Your Account Credentials",
            message=(
                f"Hi {user.first_name},\n\n"
                f"You have been added as a {role.name} "
                f"at {tenant.name}.\n\n"
                f"Your login credentials:\n"
                f"  Username: {username}\n"
                f"  Password: {password}\n\n"
                f"Please change your password after first login.\n\n"
                f"— {tenant.name} Team"
            ),
            from_email=None,
            recipient_list=[user.email],
            fail_silently=True,
        )

        return staff


class StaffUpdateSerializer(serializers.ModelSerializer):
    """Update a staff member's role."""

    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source="role",
    )

    class Meta:
        model = Staff
        fields = ["role_id"]

    def validate_role_id(self, value):
        if value.center_id != self.instance.center_id:
            raise serializers.ValidationError(
                "Role does not belong to this center.",
            )
        return value

    def update(self, instance, validated_data):
        new_role = validated_data.get("role", instance.role)
        if instance.role_id != new_role.id:
            instance.role = new_role
            instance.save(update_fields=["role"])
        return instance
