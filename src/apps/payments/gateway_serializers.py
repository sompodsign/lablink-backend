"""
UddoktaPay gateway serializers.

Handles input validation for initiating charges and output shaping
for the payment-url response.
"""

from rest_framework import serializers


class InitiateChargeSerializer(serializers.Serializer):
    """Input for the *initiate-charge* endpoint."""

    invoice_id = serializers.IntegerField(
        help_text='PK of the local Invoice to pay.',
    )
    redirect_url = serializers.URLField(
        help_text='URL the customer returns to after payment.',
    )
    cancel_url = serializers.URLField(
        required=False,
        help_text='URL the customer returns to on cancellation.',
    )


class ChargeResponseSerializer(serializers.Serializer):
    """Output returned to the frontend after a successful charge creation."""

    payment_url = serializers.URLField()
    payment_id = serializers.IntegerField(
        help_text='PK of the local Payment record created.',
    )
