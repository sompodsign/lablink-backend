import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from core.users.models import PatientProfile

User = get_user_model()
logger = logging.getLogger(__name__)


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = [
            'id',
            'phone_number',
            'date_of_birth',
            'gender',
            'blood_group',
            'address',
            'medical_history',
            'emergency_contact_name',
            'emergency_contact_phone',
            'registered_at_center',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'registered_at_center', 'created_at', 'updated_at']


class PatientSerializer(serializers.ModelSerializer):
    """Serializer for reading patient data (User + PatientProfile)."""

    patient_profile = PatientProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone_number',
            'patient_profile',
        ]
        read_only_fields = ['id', 'username']

    def get_full_name(self, obj) -> str:
        return obj.get_full_name()


class PatientRegistrationSerializer(serializers.Serializer):
    """Serializer for staff to register a walk-in patient."""

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=20, required=False, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    date_of_birth = serializers.DateField(required=False, allow_null=True, default=None)
    blood_group = serializers.ChoiceField(
        choices=PatientProfile.BloodGroup.choices,
        required=False,
        allow_blank=True,
        default='',
    )
    gender = serializers.ChoiceField(
        choices=PatientProfile.Gender.choices,
        required=False,
        allow_blank=True,
        default='',
    )
    address = serializers.CharField(required=False, allow_blank=True, default='')
    medical_history = serializers.CharField(required=False, allow_blank=True, default='')
    emergency_contact_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=''
    )
    emergency_contact_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default=''
    )

    @transaction.atomic
    def create(self, validated_data):
        center = self.context['request'].tenant

        # Auto-generate username from phone or name
        base_username = (
            validated_data.get('phone_number')
            or f"{validated_data['first_name'].lower()}.{validated_data['last_name'].lower()}"
        )
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}{counter}'
            counter += 1

        user = User.objects.create_user(
            username=username,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data.get('email', ''),
            phone_number=validated_data.get('phone_number', ''),
            center=center,
            # No password — staff-registered patients cannot log in initially
            password=None,
        )

        PatientProfile.objects.create(
            user=user,
            phone_number=validated_data.get('phone_number', ''),
            date_of_birth=validated_data.get('date_of_birth'),
            gender=validated_data.get('gender', ''),
            blood_group=validated_data.get('blood_group', ''),
            address=validated_data.get('address', ''),
            medical_history=validated_data.get('medical_history', ''),
            emergency_contact_name=validated_data.get('emergency_contact_name', ''),
            emergency_contact_phone=validated_data.get('emergency_contact_phone', ''),
            registered_at_center=center,
        )

        logger.info(
            'Patient registered',
            extra={'user_id': user.id, 'center_id': center.id},
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)
    groups = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name',
    )
    staff_role = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    center = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'password', 'confirm_password',
            'first_name', 'last_name', 'phone_number', 'groups',
            'staff_role', 'role_display', 'permissions',
            'is_superuser', 'is_active',
            'approval_status', 'center',
        )
        read_only_fields = (
            'username', 'groups', 'staff_role', 'role_display', 'permissions',
            'is_superuser', 'is_active', 'approval_status', 'center',
        )
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        if self.instance is None:  # create only
            pw = attrs.get('password')
            cpw = attrs.get('confirm_password')
            if not pw:
                raise serializers.ValidationError(
                    {'password': 'This field is required.'},
                )
            if pw != cpw:
                raise serializers.ValidationError(
                    {'confirm_password': 'Passwords do not match.'},
                )
        attrs.pop('confirm_password', None)
        return attrs

    def get_staff_role(self, obj) -> str:
        if hasattr(obj, 'staff_profile'):
            return obj.staff_profile.role.name
        return ''

    def get_permissions(self, obj) -> list[str]:
        if obj.is_superuser:
            from core.tenants.models import Permission
            return list(Permission.objects.values_list('codename', flat=True))
        if hasattr(obj, 'staff_profile'):
            return list(
                obj.staff_profile.role.permissions.values_list(
                    'codename', flat=True,
                )
            )
        if hasattr(obj, 'doctor_profile'):
            return [
                'view_patients', 'view_appointments', 'manage_appointments',
                'view_reports', 'create_reports',
            ]
        return []

    def get_role_display(self, obj) -> str:
        if obj.is_superuser:
            return 'Super Admin'
        if hasattr(obj, 'staff_profile'):
            return obj.staff_profile.get_role_display()
        if hasattr(obj, 'doctor_profile'):
            return 'Doctor'
        return ''

    def get_center(self, obj) -> dict | None:
        center = obj.center
        if center:
            return {
                'id': center.id,
                'name': center.name,
                'primary_color': center.primary_color,
                'logo_url': center.logo.url if center.logo else None,
                'tagline': center.tagline,
            }
        return None

    def create(self, validated_data):
        from core.users.views import _resolve_center_from_request

        # Resolve center from subdomain
        center = None
        request = self.context.get('request')
        if request:
            center = _resolve_center_from_request(request)

        # Auto-generate internal username
        email = validated_data['email']
        domain_suffix = center.domain if center else 'platform'
        base_username = f"{email}__{domain_suffix}"
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}_{counter}'
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data.get('phone_number', ''),
            center=center,
        )

        # Auto-create patient profile linked to center (if any)
        PatientProfile.objects.create(
            user=user,
            registered_at_center=center,
            phone_number=validated_data.get('phone_number', ''),
        )

        return user
