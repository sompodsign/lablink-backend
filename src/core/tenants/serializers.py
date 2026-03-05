import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import DiagnosticCenter, Doctor, Service, Staff

User = get_user_model()
logger = logging.getLogger(__name__)


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'title', 'description', 'icon', 'order']


class DiagnosticCenterSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()

    class Meta:
        model = DiagnosticCenter
        fields = [
            'id',
            'name',
            'domain',
            'tagline',
            'address',
            'contact_number',
            'email',
            'logo_url',
            'primary_color',
            'opening_hours',
            'years_of_experience',
            'happy_patients_count',
            'test_types_available_count',
            'lab_support_availability',
            'services',
        ]

    def get_logo_url(self, obj) -> str | None:
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
        return None

    def get_services(self, obj) -> list:
        active_services = obj.services.filter(is_active=True)
        return ServiceSerializer(active_services, many=True).data


class DoctorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.get_full_name')
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Doctor
        fields = ['id', 'name', 'email', 'specialization', 'designation', 'bio']


class DoctorManagementSerializer(serializers.ModelSerializer):
    """Full doctor management serializer for staff/admin use."""

    name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Doctor
        fields = ['id', 'name', 'email', 'username', 'specialization', 'designation', 'bio']
        read_only_fields = ['id', 'name', 'email', 'username']


class DoctorActivitySerializer(serializers.Serializer):
    """
    Summary of a doctor's recent activity at the current center.
    Not bound to a single model — combines Appointments + TestOrders.
    """

    doctor = DoctorSerializer()
    total_appointments = serializers.IntegerField()
    total_test_orders = serializers.IntegerField()
    recent_appointments = serializers.ListField(child=serializers.DictField())


class StaffSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = Staff
        fields = ['id', 'name', 'email', 'role', 'role_display']
