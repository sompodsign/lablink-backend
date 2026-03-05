from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id',
            'appointment',
            'test_order',
            'patient_name',
            'amount',
            'transaction_id',
            'method',
            'method_display',
            'status',
            'status_display',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_patient_name(self, obj) -> str:
        return obj.appointment.patient.get_full_name()


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'appointment',
            'test_order',
            'amount',
            'transaction_id',
            'method',
            'status',
        ]

    def validate_appointment(self, appointment):
        tenant = self.context['request'].tenant
        if appointment.center_id != tenant.id:
            raise serializers.ValidationError(
                'Appointment does not belong to this center.'
            )
        return appointment

    def validate_test_order(self, test_order):
        if test_order is None:
            return test_order
        tenant = self.context['request'].tenant
        if test_order.center_id != tenant.id:
            raise serializers.ValidationError(
                'Test order does not belong to this center.'
            )
        return test_order
