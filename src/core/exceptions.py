"""Custom DRF exception handler.

Catches unhandled database IntegrityError (duplicate key, FK violations, etc.)
and returns a clean JSON 400 response instead of a 500 HTML error page.
"""

import logging

from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Wrap the default DRF handler, then catch IntegrityError."""
    response = exception_handler(exc, context)

    if response is not None:
        return response

    # IntegrityError → 400 with a human-readable message
    if isinstance(exc, IntegrityError):
        detail = str(exc)
        # Extract the useful part from Postgres error messages
        if "DETAIL:" in detail:
            detail = detail.split("DETAIL:")[1].strip().split("\n")[0]
        elif "unique constraint" in detail.lower():
            detail = "A record with this value already exists."
        else:
            detail = "Database constraint violated. Please check your input."

        logger.warning(
            "IntegrityError in %s: %s",
            context.get("view", ""),
            exc,
        )
        return Response(
            {"detail": detail},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return None
