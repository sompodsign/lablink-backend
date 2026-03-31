"""Serializers for the AI app."""

from rest_framework import serializers


ALLOWED_IMAGE_TYPES = frozenset({
    'image/jpeg',
    'image/png',
    'image/webp',
})

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


class ReportExtractionSerializer(serializers.Serializer):
    """Validates the image upload for AI report extraction."""

    image = serializers.ImageField(
        help_text='Photograph or scan of the diagnostic report (JPEG/PNG/WebP, max 10 MB).',
    )
    test_type_id = serializers.IntegerField(
        help_text='ID of the test type to look up the expected result fields template.',
    )

    def validate_image(self, value):
        if value.content_type not in ALLOWED_IMAGE_TYPES:
            raise serializers.ValidationError(
                f'Unsupported image type: {value.content_type}. '
                f'Allowed types: JPEG, PNG, WebP.'
            )
        if value.size > MAX_IMAGE_SIZE:
            raise serializers.ValidationError(
                f'Image too large ({value.size / 1024 / 1024:.1f} MB). '
                f'Maximum size is 10 MB.'
            )
        return value
