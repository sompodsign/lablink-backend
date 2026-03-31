import logging
import secrets

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.notifications.emails import EmailType, send_email

from .models import (
    DiagnosticCenter,
    Doctor,
    Permission,
    PlatformSettings,
    Role,
    Service,
    Staff,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "title", "description", "icon", "order"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = self.context.get("language", "en")
        if lang == "bn":
            data["title"] = instance.title_bn or data["title"]
            data["description"] = instance.description_bn or data["description"]
        return data


class DiagnosticCenterSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()

    class Meta:
        model = DiagnosticCenter
        fields = [
            "id",
            "name",
            "domain",
            "language",
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
            # Superadmin master switches (read-only for all)
            "can_use_sms",
            "can_use_email",
            "can_use_ai",
            # Lab Admin operational toggles
            "sms_enabled",
            "email_notifications_enabled",
            "send_sms_invoice",
            "send_email_invoice",
        ]

    def get_logo_url(self, obj) -> str | None:
        if obj.logo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.logo.url)
        return None

    def get_services(self, obj) -> list:
        active_services = obj.services.filter(is_active=True)
        return ServiceSerializer(
            active_services,
            many=True,
            context={"language": obj.language},
        ).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = instance.language
        if lang == "bn":
            data["tagline"] = instance.tagline_bn or data["tagline"]
        return data


class CenterSettingsSerializer(serializers.ModelSerializer):
    """Lab-Admin-editable center settings.

    can_use_sms / can_use_email / can_use_ai are read-only here —
    only Superadmin can write them (via the superadmin center API).
    Backend enforces: if can_use_* is False, the corresponding
    operational toggles are coerced to False regardless of input.
    """

    logo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DiagnosticCenter
        fields = [
            "id",
            "name",
            "language",
            "tagline",
            "tagline_bn",
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
            "doctor_visit_fee",
            # Print layout
            "paper_size",
            "use_preprinted_paper",
            "print_header_margin_mm",
            "print_footer_margin_mm",
            # Superadmin master switches (read-only)
            "can_use_sms",
            "can_use_email",
            "can_use_ai",
            # Center Admin master toggles
            "use_sms",
            "use_email",
            "use_ai",
            # Lab Admin operational toggles
            "sms_enabled",
            "email_notifications_enabled",
            "send_sms_invoice",
            "send_email_invoice",
        ]
        read_only_fields = [
            "id",
            "logo_url",
            # Only Superadmin may change these via superadmin API
            "can_use_sms",
            "can_use_email",
            "can_use_ai",
        ]

    def validate(self, attrs):
        """Enforce master switch gates on operational toggles."""
        instance = self.instance

        def can_use(flag: str) -> bool:
            """Return True if the superadmin master switch is on."""
            return getattr(instance, flag, False) if instance else False

        # ── SMS gate ──────────────────────────────────────────────
        if not can_use("can_use_sms"):
            attrs["use_sms"] = False
            attrs["sms_enabled"] = False
            attrs["send_sms_invoice"] = False
        else:
            # If center admin turns off SMS master toggle, disable sub-toggles
            use_sms = attrs.get("use_sms", getattr(instance, "use_sms", True))
            if not use_sms:
                attrs["sms_enabled"] = False
                attrs["send_sms_invoice"] = False

        # ── Email gate ────────────────────────────────────────────
        if not can_use("can_use_email"):
            attrs["use_email"] = False
            attrs["email_notifications_enabled"] = False
            attrs["send_email_invoice"] = False
        else:
            use_email = attrs.get("use_email", getattr(instance, "use_email", True))
            if not use_email:
                attrs["email_notifications_enabled"] = False
                attrs["send_email_invoice"] = False

        # ── AI gate ───────────────────────────────────────────────
        if not can_use("can_use_ai"):
            attrs["use_ai"] = False
        return attrs

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
        fields = [
            "id",
            "name",
            "email",
            "specialization",
            "designation",
            "bio",
            "visit_fee",
            "available_from",
            "available_to",
            "slot_duration_minutes",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = self.context.get("language", "en")
        if lang == "bn":
            data["specialization"] = (
                instance.specialization_bn or data["specialization"]
            )
            data["designation"] = instance.designation_bn or data["designation"]
            data["bio"] = instance.bio_bn or data["bio"]
        return data


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
            "visit_fee",
            "available_from",
            "available_to",
            "slot_duration_minutes",
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
    visit_fee = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default="0.00"
    )

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

            password = secrets.token_urlsafe(10)
            user = User.objects.create_user(
                username=username,
                email=validated_data.get("email", ""),
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                phone_number=validated_data.get("phone_number", ""),
                password=password,
                center=tenant,
            )

            doctor = Doctor.objects.create(
                user=user,
                specialization=validated_data["specialization"],
                designation=validated_data["designation"],
                bio=validated_data.get("bio", ""),
                visit_fee=validated_data.get("visit_fee", "0.00"),
            )

        # Send credentials email (outside transaction)
        if user.email:
            send_email(
                EmailType.DOCTOR_CREDENTIALS,
                recipient=user.email,
                context={
                    "first_name": user.first_name,
                    "center_name": tenant.name,
                    "username": username,
                    "password": password,
                },
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

    def validate(self, data):
        from apps.subscriptions.models import Subscription

        tenant = self.context["request"].tenant
        try:
            sub = (
                Subscription.objects.select_related("plan")
                .filter(
                    center=tenant,
                )
                .latest("started_at")
            )
            max_staff = sub.plan.max_staff
        except Subscription.DoesNotExist:
            max_staff = -1

        if max_staff != -1:
            current_count = Staff.objects.filter(center=tenant).count()
            if current_count >= max_staff:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            f"Staff limit reached ({current_count}/{max_staff}). "
                            f"Upgrade your plan to add more staff members."
                        ]
                    }
                )
        return data

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
                center=tenant,
            )

            staff = Staff.objects.create(
                user=user,
                center=tenant,
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
                    "center_name": tenant.name,
                    "username": username,
                    "password": password,
                },
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


class PlatformSettingsSerializer(serializers.ModelSerializer):
    """SuperAdmin editable platform-wide settings."""

    class Meta:
        model = PlatformSettings
        fields = ["language", "updated_at"]
        read_only_fields = ["updated_at"]
