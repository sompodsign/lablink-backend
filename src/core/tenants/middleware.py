
import logging

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.tenants.models import DiagnosticCenter

logger = logging.getLogger(__name__)
User = get_user_model()


class TenantMiddleware:
    """
    Middleware to identify the current tenant from the authenticated user.
    Uses JWT token from the Authorization header to identify the user,
    then reads their `center` FK directly.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        request.tenant = None

        # Try to get user from JWT token
        user = self._get_user_from_jwt(request)
        if user:
            request.tenant = self._get_tenant_for_user(user)

        # Block deactivated centers (superadmins bypass)
        if (
            request.tenant
            and not request.tenant.is_active
            and user
            and not user.is_superuser
        ):
            from django.http import JsonResponse
            return JsonResponse(
                {
                    'detail': (
                        'This diagnostic center has been deactivated. '
                        'Please contact the platform administrator.'
                    ),
                },
                status=403,
            )

        response = self.get_response(request)
        return response

    def _get_user_from_jwt(self, request):
        try:
            auth_result = self.jwt_auth.authenticate(request)
            if auth_result:
                return auth_result[0]  # (user, token)
        except Exception:
            pass
        return None

    def _get_tenant_for_user(self, user):
        """Return the user's center directly from User.center FK."""
        if user.center_id:
            return user.center

        # Superadmin fallback — they have center=None
        if user.is_superuser:
            return DiagnosticCenter.objects.first()

        return None
