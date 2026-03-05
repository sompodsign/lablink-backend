from rest_framework import serializers

from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id',
            'patient',
            'patient_name',
            'center',
            'doctor',
            'doctor_name',
            'date',
            'time',
            'status',
            'symptoms',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_patient_name(self, obj) -> str:
        return obj.patient.get_full_name()

    def get_doctor_name(self, obj) -> str:
        if obj.doctor:
            return str(obj.doctor)
        return ''


class ConsultationUpdateSerializer(serializers.ModelSerializer):
    """Used by doctors to add clinical notes/symptoms to an appointment."""

    class Meta:
        model = Appointment
        fields = ['symptoms', 'status']
