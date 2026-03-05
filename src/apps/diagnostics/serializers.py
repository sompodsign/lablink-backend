import logging

from rest_framework import serializers

from apps.diagnostics.models import CenterTestPricing, Report, TestOrder, TestType

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


class TestOrderSerializer(serializers.ModelSerializer):
    test_type_name = serializers.CharField(source='test_type.name', read_only=True)
    patient_name = serializers.SerializerMethodField()
    ordered_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TestOrder
        fields = [
            'id',
            'appointment',
            'center',
            'test_type',
            'test_type_name',
            'ordered_by',
            'ordered_by_name',
            'patient_name',
            'status',
            'priority',
            'clinical_notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'center', 'ordered_by', 'created_at', 'updated_at']

    def get_patient_name(self, obj) -> str:
        return obj.appointment.patient.get_full_name()

    def get_ordered_by_name(self, obj) -> str:
        if obj.ordered_by:
            return obj.ordered_by.get_full_name()
        return ''


class TestOrderCreateSerializer(serializers.ModelSerializer):
    """Used by doctors to prescribe a test."""

    class Meta:
        model = TestOrder
        fields = [
            'appointment',
            'test_type',
            'priority',
            'clinical_notes',
        ]

    def validate_appointment(self, appointment):
        tenant = self.context['request'].tenant
        if appointment.center_id != tenant.id:
            raise serializers.ValidationError(
                'Appointment does not belong to this center.'
            )
        return appointment

    def validate_test_type(self, test_type):
        tenant = self.context['request'].tenant
        # Ensure the test type is available at this center
        pricing = CenterTestPricing.objects.filter(
            center=tenant, test_type=test_type, is_available=True
        ).first()
        if not pricing:
            raise serializers.ValidationError(
                'This test type is not available at this center.'
            )
        return test_type

    def create(self, validated_data):
        request = self.context['request']
        validated_data['center'] = request.tenant
        validated_data['ordered_by'] = request.user
        return super().create(validated_data)


class TestOrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Used by lab technicians to update test order status."""

    class Meta:
        model = TestOrder
        fields = ['status']


class ReportSerializer(serializers.ModelSerializer):
    test_type_name = serializers.CharField(source='test_type.name', read_only=True)
    patient_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id',
            'appointment',
            'test_order',
            'test_type',
            'test_type_name',
            'patient_name',
            'file',
            'result_text',
            'result_data',
            'status',
            'status_display',
            'verified_by',
            'is_delivered_online',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'verified_by', 'created_at', 'updated_at']

    def get_patient_name(self, obj) -> str:
        return obj.appointment.patient.get_full_name()


class ReportCreateSerializer(serializers.ModelSerializer):
    """Used by lab technicians to create a report from a test order."""

    class Meta:
        model = Report
        fields = [
            'test_order',
            'result_text',
            'result_data',
            'file',
        ]

    def validate_test_order(self, test_order):
        tenant = self.context['request'].tenant
        if test_order.center_id != tenant.id:
            raise serializers.ValidationError(
                'Test order does not belong to this center.'
            )
        if hasattr(test_order, 'report'):
            raise serializers.ValidationError(
                'A report already exists for this test order.'
            )
        return test_order

    def create(self, validated_data):
        test_order = validated_data['test_order']
        validated_data['appointment'] = test_order.appointment
        validated_data['test_type'] = test_order.test_type
        # Advance test order status
        test_order.status = TestOrder.Status.COMPLETED
        test_order.save(update_fields=['status', 'updated_at'])
        return super().create(validated_data)
