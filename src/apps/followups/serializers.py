import logging

from rest_framework import serializers

from .models import FollowUp

logger = logging.getLogger(__name__)


class _PatientSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.SerializerMethodField()
    phone = serializers.CharField(source="phone_number", default="")

    def get_full_name(self, obj) -> str:
        return obj.get_full_name() or obj.username


class _DoctorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.username


class _AppointmentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField()


class _CreatorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        return obj.get_full_name() or obj.username


class FollowUpSerializer(serializers.ModelSerializer):
    patient = _PatientSerializer(read_only=True)
    doctor = _DoctorSerializer(read_only=True)
    appointment = _AppointmentSerializer(read_only=True)
    created_by = _CreatorSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = FollowUp
        fields = [
            "id",
            "patient",
            "doctor",
            "appointment",
            "scheduled_date",
            "reason",
            "notes",
            "status",
            "cancel_reason",
            "notify_patient",
            "is_overdue",
            "created_by",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "cancel_reason",
            "is_overdue",
            "completed_at",
            "created_at",
            "updated_at",
        ]


class FollowUpCreateSerializer(serializers.ModelSerializer):
    """Write serializer — center and created_by injected from request context."""

    class Meta:
        model = FollowUp
        fields = [
            "patient",
            "doctor",
            "scheduled_date",
            "reason",
            "notes",
        ]
        extra_kwargs = {
            "reason": {"required": False, "allow_blank": True, "default": ""},
        }

    def validate_patient(self, value):
        center = self.context["request"].tenant
        if value is None:
            raise serializers.ValidationError("Patient is required.")
        if value.center_id != center.id:
            raise serializers.ValidationError("Patient does not belong to this center.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["center"] = request.tenant
        validated_data["created_by"] = request.user
        validated_data["updated_by"] = request.user
        return super().create(validated_data)


class FollowUpUpdateSerializer(serializers.ModelSerializer):
    """Partial update serializer — only editable fields allowed on PENDING follow-ups."""

    class Meta:
        model = FollowUp
        fields = [
            "scheduled_date",
            "reason",
            "notes",
            "doctor",
        ]

    def update(self, instance, validated_data):
        request = self.context["request"]
        validated_data["updated_by"] = request.user
        return super().update(instance, validated_data)


class CancelSerializer(serializers.Serializer):
    cancel_reason = serializers.CharField(required=True, allow_blank=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CompleteSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")
