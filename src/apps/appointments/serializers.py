from rest_framework import serializers

from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "patient_name",
            "center",
            "doctor",
            "doctor_name",
            "date",
            "time",
            "status",
            "symptoms",
            "guest_name",
            "guest_phone",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_patient_name(self, obj) -> str:
        if obj.patient:
            return obj.patient.get_full_name()
        return obj.guest_name or "Guest"

    def get_doctor_name(self, obj) -> str:
        if obj.doctor:
            return str(obj.doctor)
        return ""


class ConsultationUpdateSerializer(serializers.ModelSerializer):
    """Used by doctors to add clinical notes/symptoms to an appointment."""

    class Meta:
        model = Appointment
        fields = ["symptoms", "status"]


class PatientBookingSerializer(serializers.Serializer):
    """Patient self-books an appointment."""

    doctor = serializers.IntegerField(required=False, allow_null=True)
    date = serializers.DateField()
    time = serializers.TimeField()
    symptoms = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_date(self, value):
        from datetime import date as dt_date

        if value < dt_date.today():
            raise serializers.ValidationError("Cannot book an appointment in the past.")
        return value

    def validate_doctor(self, value):
        if value is None:
            return value
        from core.tenants.models import Doctor

        request = self.context["request"]
        tenant = request.tenant
        if not Doctor.objects.filter(pk=value, user__center=tenant).exists():
            raise serializers.ValidationError("Doctor does not belong to this center.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        from core.tenants.models import Doctor

        doctor_id = validated_data.pop("doctor", None)
        doctor = Doctor.objects.get(pk=doctor_id) if doctor_id else None

        return Appointment.objects.create(
            patient=request.user,
            center=request.tenant,
            doctor=doctor,
            status="PENDING",
            **validated_data,
        )
