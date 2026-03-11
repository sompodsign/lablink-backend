import logging
from datetime import date

from rest_framework import serializers

from apps.diagnostics.models import (
    CenterTestPricing,
    ReferringDoctor,
    Report,
    ReportTemplate,
    TestOrder,
    TestType,
)
from apps.diagnostics.services.calculations import auto_calculate
from apps.diagnostics.services.flagging import flag_report_results

logger = logging.getLogger(__name__)


class TestTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestType
        fields = '__all__'


class CenterTestPricingSerializer(serializers.ModelSerializer):
    test_type_details = TestTypeSerializer(source='test_type', read_only=True)

    class Meta:
        model = CenterTestPricing
        fields = '__all__'


# ─── Report Template ───────────────────────────────────────────────

class ReportTemplateSerializer(serializers.ModelSerializer):
    test_type_name = serializers.CharField(source='test_type.name', read_only=True)

    class Meta:
        model = ReportTemplate
        fields = [
            'id',
            'center',
            'test_type',
            'test_type_name',
            'fields',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'center', 'created_at', 'updated_at']


# ─── Referring Doctor ──────────────────────────────────────────────

class ReferringDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferringDoctor
        fields = [
            'id',
            'name',
            'designation',
            'institution',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'center', 'created_at']

    def create(self, validated_data):
        validated_data['center'] = self.context['request'].tenant
        return super().create(validated_data)


# ─── Test Order ────────────────────────────────────────────────────

class TestOrderSerializer(serializers.ModelSerializer):
    test_type_name = serializers.CharField(source='test_type.name', read_only=True)
    patient_name = serializers.SerializerMethodField()
    has_report = serializers.SerializerMethodField()
    report_id = serializers.SerializerMethodField()

    class Meta:
        model = TestOrder
        fields = [
            'id',
            'patient',
            'patient_name',
            'center',
            'test_type',
            'test_type_name',
            'appointment',
            'referring_doctor_name',
            'created_by',
            'status',
            'priority',
            'clinical_notes',
            'has_report',
            'report_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'center', 'created_by', 'created_at', 'updated_at']

    def get_patient_name(self, obj) -> str:
        return obj.patient.get_full_name()

    def get_has_report(self, obj) -> bool:
        return hasattr(obj, 'report')

    def get_report_id(self, obj) -> int | None:
        return obj.report.id if hasattr(obj, 'report') else None


class TestOrderCreateSerializer(serializers.ModelSerializer):
    """Used by staff to create a test order for a walk-in patient."""

    class Meta:
        model = TestOrder
        fields = [
            'patient',
            'test_type',
            'appointment',
            'referring_doctor_name',
            'priority',
            'clinical_notes',
        ]

    def validate_test_type(self, test_type):
        tenant = self.context['request'].tenant
        pricing = CenterTestPricing.objects.filter(
            center=tenant, test_type=test_type, is_available=True
        ).first()
        if not pricing:
            raise serializers.ValidationError(
                'This test type is not available at this center.'
            )
        return test_type

    def validate_appointment(self, appointment):
        if appointment:
            tenant = self.context['request'].tenant
            if appointment.center_id != tenant.id:
                raise serializers.ValidationError(
                    'Appointment does not belong to this center.'
                )
        return appointment

    def create(self, validated_data):
        request = self.context['request']
        validated_data['center'] = request.tenant
        validated_data['created_by'] = request.user
        # Auto-set referring doctor name if the creator is a doctor
        if hasattr(request.user, 'doctor_profile') and not validated_data.get('referring_doctor_name'):
            validated_data['referring_doctor_name'] = request.user.get_full_name()
        return super().create(validated_data)


class TestOrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Used by lab technicians to update test order status."""

    class Meta:
        model = TestOrder
        fields = ['status']


# ─── Report ────────────────────────────────────────────────────────

class ReportSerializer(serializers.ModelSerializer):
    test_type_name = serializers.CharField(source='test_type.name', read_only=True)
    patient_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    referring_doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id',
            'test_order',
            'appointment',
            'test_type',
            'test_type_name',
            'patient_name',
            'referring_doctor_name',
            'file',
            'result_text',
            'result_data',
            'status',
            'status_display',
            'verified_by',
            'is_delivered_online',
            'access_token',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'verified_by', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        # Auto-calculate and re-flag result values when result_data is updated
        result_data = validated_data.get('result_data')
        if result_data:
            result_data = auto_calculate(result_data)
            template = ReportTemplate.objects.filter(
                center=instance.test_order.center,
                test_type=instance.test_type,
            ).first()
            template_fields = template.fields if template else None
            validated_data['result_data'] = flag_report_results(
                result_data, template_fields
            )
        return super().update(instance, validated_data)

    def get_patient_name(self, obj) -> str:
        return obj.test_order.patient.get_full_name()

    def get_referring_doctor_name(self, obj) -> str:
        return obj.test_order.referring_doctor_name or ''


class ReportCreateSerializer(serializers.Serializer):
    """Lab technician creates a report by selecting a test type and patient directly.
    A test order is auto-created behind the scenes — unless an existing one is given."""

    test_order = serializers.PrimaryKeyRelatedField(
        queryset=TestOrder.objects.all(), required=False, allow_null=True,
    )
    test_type = serializers.PrimaryKeyRelatedField(
        queryset=TestType.objects.all(), required=False,
    )
    patient = serializers.PrimaryKeyRelatedField(
        queryset=__import__(
            'django.contrib.auth', fromlist=['get_user_model'],
        ).get_user_model().objects.all(),
        required=False,
    )
    referring_doctor_name = serializers.CharField(
        required=False, allow_blank=True, default='',
    )
    result_text = serializers.CharField(
        required=False, allow_blank=True, default='',
    )
    result_data = serializers.JSONField(required=False, default=dict)
    file = serializers.FileField(
        required=False, allow_null=True, default=None,
    )

    def validate_test_order(self, test_order):
        if test_order is None:
            return None
        tenant = self.context['request'].tenant
        if test_order.center_id != tenant.id:
            raise serializers.ValidationError(
                'Test order does not belong to this center.'
            )
        if hasattr(test_order, 'report'):
            raise serializers.ValidationError(
                'This test order already has a report.'
            )
        return test_order

    def validate_test_type(self, test_type):
        tenant = self.context['request'].tenant
        pricing = CenterTestPricing.objects.filter(
            center=tenant, test_type=test_type, is_available=True,
        ).first()
        if not pricing:
            raise serializers.ValidationError(
                'This test type is not available at this center.'
            )
        return test_type

    def validate(self, attrs):
        test_order = attrs.get('test_order')
        if test_order:
            # Inherit from order; ignore manual patient/test_type/doctor
            attrs['patient'] = test_order.patient
            attrs['test_type'] = test_order.test_type
            attrs['referring_doctor_name'] = (
                test_order.referring_doctor_name or ''
            )
        else:
            if not attrs.get('test_type'):
                raise serializers.ValidationError(
                    {'test_type': 'This field is required.'}
                )
            if not attrs.get('patient'):
                raise serializers.ValidationError(
                    {'patient': 'This field is required.'}
                )
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        tenant = request.tenant
        existing_order = validated_data.pop('test_order', None)

        if existing_order:
            test_order = existing_order
            # Mark the order as completed if it isn't already
            if test_order.status != TestOrder.Status.COMPLETED:
                test_order.status = TestOrder.Status.COMPLETED
                test_order.save(update_fields=['status'])
        else:
            # Auto-create a test order (original behaviour)
            test_order = TestOrder.objects.create(
                patient=validated_data['patient'],
                center=tenant,
                test_type=validated_data['test_type'],
                referring_doctor_name=validated_data.get(
                    'referring_doctor_name', '',
                ),
                created_by=request.user,
                status=TestOrder.Status.COMPLETED,
            )

        # Auto-calculate derived fields, then flag all values
        result_data = validated_data.get('result_data', {})
        if result_data:
            result_data = auto_calculate(result_data)
            template = ReportTemplate.objects.filter(
                center=tenant,
                test_type=validated_data['test_type'],
            ).first()
            template_fields = template.fields if template else None
            result_data = flag_report_results(result_data, template_fields)

        # Create the report
        report = Report.objects.create(
            test_order=test_order,
            test_type=validated_data['test_type'],
            result_text=validated_data.get('result_text', ''),
            result_data=result_data,
            file=validated_data.get('file'),
            created_by=request.user,
        )
        return report


# ─── Report Print Data ─────────────────────────────────────────────

class ReportPrintSerializer(serializers.ModelSerializer):
    """Comprehensive serializer that returns everything needed to print a report."""

    center = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    referring_doctor = serializers.SerializerMethodField()
    lab_technician = serializers.SerializerMethodField()
    previous_results = serializers.SerializerMethodField()
    test_type_name = serializers.CharField(source='test_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id',
            'test_type_name',
            'result_text',
            'result_data',
            'status',
            'status_display',
            'created_at',
            'updated_at',
            'center',
            'patient',
            'referring_doctor',
            'lab_technician',
            'access_token',
            'previous_results',
        ]

    def _calculate_age(self, dob):
        if not dob:
            return None
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def get_center(self, obj):
        center = obj.test_order.center
        logo_url = None
        if center.logo:
            request = self.context.get('request')
            if request:
                logo_url = request.build_absolute_uri(center.logo.url)
            else:
                logo_url = center.logo.url
        return {
            'name': center.name,
            'tagline': center.tagline,
            'address': center.address,
            'contact_number': center.contact_number,
            'email': center.email or '',
            'logo': logo_url,
            'primary_color': center.primary_color,
        }

    def get_patient(self, obj):
        patient = obj.test_order.patient
        profile = getattr(patient, 'patient_profile', None)
        dob = profile.date_of_birth if profile else None
        return {
            'name': patient.get_full_name(),
            'id': f'P-{patient.id:05d}',
            'age': self._calculate_age(dob),
            'gender': profile.gender if profile else '',
            'phone': patient.phone_number or (profile.phone_number if profile else ''),
            'blood_group': profile.blood_group if profile else '',
        }

    def get_referring_doctor(self, obj):
        return obj.test_order.referring_doctor_name or ''

    def get_lab_technician(self, obj):
        # Use report.created_by (the lab tech who authored the report)
        tech_user = obj.created_by
        if not tech_user:
            return None
        staff = getattr(tech_user, 'staff_profile', None)
        return {
            'name': tech_user.get_full_name(),
            'role': staff.get_role_display() if staff else '',
        }

    def get_previous_results(self, obj):
        """Return the most recent previous report for the same patient+test type."""
        previous = (
            Report.objects.filter(
                test_order__patient=obj.test_order.patient,
                test_type=obj.test_type,
                is_deleted=False,
            )
            .exclude(id=obj.id)
            .order_by('-created_at')
            .values('result_data', 'created_at')
            .first()
        )
        if not previous or not previous.get('result_data'):
            return None
        return {
            'result_data': previous['result_data'],
            'date': previous['created_at'].strftime('%d %b %Y'),
        }
