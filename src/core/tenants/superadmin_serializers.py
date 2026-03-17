import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.users.models import PatientProfile

from .models import DiagnosticCenter, Doctor, Staff

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

    class Meta(SuperadminCenterSerializer.Meta):
        fields = SuperadminCenterSerializer.Meta.fields + [
            "years_of_experience",
            "happy_patients_count",
            "test_types_available_count",
            "lab_support_availability",
        ]


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
