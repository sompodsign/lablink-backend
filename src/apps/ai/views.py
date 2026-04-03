"""Views for the AI app — report extraction endpoint."""

import logging

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.client import ExtractionResult, extract_report_data
from apps.ai.models import AICreditUsageLog
from apps.ai.serializers import ReportExtractionSerializer
from apps.ai.services import (
    AIFeatureDisabledError,
    InsufficientAICreditsError,
    check_ai_access,
    deduct_ai_credit,
)
from apps.diagnostics.models import ReportTemplate
from core.tenants.permissions import IsCenterStaff

logger = logging.getLogger(__name__)


class ReportExtractionView(APIView):
    """Extract structured result data from a diagnostic report image.

    Accepts a photograph/scan of a lab report and uses AI (Claude Haiku)
    to extract structured result values matching the center's report
    template for the given test type.

    **Gating**: Requires center AI to be active and sufficient AI credits.
    **Permission**: Authenticated center staff only.
    """

    permission_classes = [permissions.IsAuthenticated, IsCenterStaff]

    @extend_schema(
        tags=["AI"],
        summary="Extract report data from image",
        description=(
            "Upload a photograph or scan of a diagnostic report. "
            "AI will extract structured result values matching the center's "
            "report template for the given test type. "
            "Consumes 1 AI credit per extraction."
        ),
        request={
            "multipart/form-data": ReportExtractionSerializer,
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "result_data": {
                        "type": "object",
                        "description": "Extracted result data keyed by field name",
                    },
                    "credits_remaining": {
                        "type": "integer",
                        "description": "AI credits remaining after this extraction",
                    },
                },
            },
        },
        examples=[
            OpenApiExample(
                "Successful CBC extraction",
                value={
                    "result_data": {
                        "Hemoglobin": {
                            "value": "14.5",
                            "unit": "g/dL",
                            "finding": "Normal",
                        },
                        "Total WBC Count": {
                            "value": "8500",
                            "unit": "/cumm",
                            "finding": "Normal",
                        },
                    },
                    "credits_remaining": 499,
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        center = request.tenant

        # ── 1. Validate input ─────────────────────────────────────
        serializer = ReportExtractionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image = serializer.validated_data["image"]
        test_type_id = serializer.validated_data["test_type_id"]

        # ── 2. Check AI access (gate + credits) ──────────────────
        try:
            subscription = check_ai_access(center)
        except AIFeatureDisabledError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except InsufficientAICreditsError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        # ── 3. Fetch report template ─────────────────────────────
        try:
            template = ReportTemplate.objects.select_related(
                "test_type",
            ).get(
                center=center,
                test_type_id=test_type_id,
            )
        except ReportTemplate.DoesNotExist:
            return Response(
                {
                    "detail": (
                        "No report template found for this test type. "
                        "Please create a template first."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── 4. Call AI ────────────────────────────────────────────
        image_bytes = image.read()
        mime_type = image.content_type

        try:
            result: ExtractionResult = extract_report_data(
                image_bytes=image_bytes,
                mime_type=mime_type,
                template_fields=template.fields,
                test_type_name=template.test_type.name,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception:
            logger.exception("AI extraction failed")
            return Response(
                {"detail": "AI extraction failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── 5. Deduct credit ─────────────────────────────────────
        try:
            deduct_ai_credit(
                center=center,
                task_type=AICreditUsageLog.TaskType.REPORT_EXTRACTION,
                performed_by=request.user,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                metadata={
                    "test_type_id": test_type_id,
                    "test_type_name": template.test_type.name,
                    "model": result.model,
                },
            )
        except InsufficientAICreditsError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        subscription.refresh_from_db()

        logger.info(
            "AI report extraction completed",
            extra={
                "center": center.name,
                "test_type": template.test_type.name,
                "user": request.user.id,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            },
        )

        return Response(
            {
                "result_data": result.result_data,
                "credits_remaining": subscription.available_ai_credits,
            }
        )
