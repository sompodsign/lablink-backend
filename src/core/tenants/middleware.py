import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.tenants.models import DiagnosticCenter

logger = logging.getLogger(__name__)
User = get_user_model()

# Subdomains that are not tenant identifiers — skip domain validation for these
_RESERVED_SUBDOMAINS = {"api", "www", "lablink", ""}
_BASE_DOMAIN = "lablink.bd"
_BASE_DOMAIN_LOCAL = "localhost"
_SUBDOMAIN_CACHE_TTL = 1200  # 20 minutes

# URLs exempt from soft-block (always allowed even when expired)
_SOFT_BLOCK_EXEMPT_PREFIXES = (
    "/api/token/",
    "/api/auth/",
    "/api/public/",
    "/api/subscriptions/",
    "/admin/",
)

# Read endpoints allowed even when subscription is INACTIVE (so user can see subscription and pay)
_INACTIVE_READ_EXEMPT_PREFIXES = (
    "/api/subscriptions/my-subscription/",
    "/api/subscriptions/my-invoices/",
    "/api/subscriptions/payment-info/",
    "/api/subscriptions/status/",
    "/api/subscriptions/gateway/",
    "/api/subscriptions/payment-submissions/",
)

# HTTP methods considered "write" operations
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Subscription statuses that trigger soft-block (writes only)
_SOFT_BLOCKED_STATUSES = {"EXPIRED", "CANCELLED"}

# Subscription statuses that trigger hard-block (ALL methods)
_HARD_BLOCKED_STATUSES = {"INACTIVE", "NONE"}


def _extract_subdomain(host: str) -> str | None:
    """
    Extract the subdomain from a Host header value.
    Returns None if the host is the bare domain or a reserved subdomain.

    Examples:
        'alpha.lablink.bd'  -> 'alpha'
        'lablink.bd'        -> None  (bare domain)
        'api.lablink.bd'    -> None  (reserved)
        'localhost'         -> None  (local dev)
    """
    host = host.split(":")[0].lower()  # strip port
    if host.endswith(_BASE_DOMAIN):
        base = _BASE_DOMAIN
    elif host.endswith(_BASE_DOMAIN_LOCAL):
        base = _BASE_DOMAIN_LOCAL
    else:
        return None  # unknown domain — skip
    subdomain = host[: -(len(base))].rstrip(".")
    if subdomain in _RESERVED_SUBDOMAINS:
        return None
    return subdomain or None


def _is_registered_subdomain(subdomain: str) -> bool:
    """
    Returns True if the subdomain maps to a DiagnosticCenter.
    Result is cached in Redis for _SUBDOMAIN_CACHE_TTL seconds to avoid
    a DB hit on every request.
    """
    cache_key = f"tenant_domain_exists:{subdomain}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    exists = DiagnosticCenter.objects.filter(domain=subdomain).exists()
    cache.set(cache_key, exists, _SUBDOMAIN_CACHE_TTL)
    return exists


def _get_subscription_status(center) -> str | None:
    """
    Get the subscription status for a center, cached for 5 minutes.
    Returns the status string or None if no subscription exists.
    """
    cache_key = f"sub_status:{center.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from apps.subscriptions.models import Subscription

    try:
        sub = Subscription.objects.filter(center=center).latest("started_at")
        status = sub.status
    except Subscription.DoesNotExist:
        status = "NONE"

    cache.set(cache_key, status, 300)  # 5 minutes
    return status


class TenantMiddleware:
    """
    Middleware to identify the current tenant from the authenticated user.
    Uses JWT token from the Authorization header to identify the user,
    then reads their `center` FK directly.

    Also validates subdomain-based access: requests to unregistered subdomains
    (e.g. unknown.lablink.bd) are rejected with HTTP 404.

    Soft-blocks centers with expired subscriptions: allows login and read
    operations but blocks write operations (POST, PUT, PATCH, DELETE).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        request.tenant = None
        request.subscription_status = None

        # ── Subdomain validation (cached — 1 DB hit per 5 min per subdomain) ─
        subdomain = _extract_subdomain(request.get_host())
        if subdomain is not None and not _is_registered_subdomain(subdomain):
            from django.http import JsonResponse

            logger.warning("Unregistered subdomain access attempt: %s", subdomain)
            return JsonResponse(
                {"detail": "Tenant not found."},
                status=404,
            )

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
                    "detail": (
                        "This diagnostic center has been deactivated. "
                        "Please contact the platform administrator."
                    ),
                },
                status=403,
            )

        # ── Subscription blocking ────────────────────────────────────────
        if request.tenant and user and not user.is_superuser:
            sub_status = _get_subscription_status(request.tenant)
            request.subscription_status = sub_status

            # INACTIVE or NONE: block all writes, allow specific reads for subscription/payment flow
            if sub_status in _HARD_BLOCKED_STATUSES:
                is_hard_block_exempt = any(
                    request.path.startswith(prefix)
                    for prefix in _INACTIVE_READ_EXEMPT_PREFIXES
                )
                if not is_hard_block_exempt:
                    from django.http import JsonResponse

                    code = "subscription_inactive" if sub_status == "INACTIVE" else "no_subscription"
                    detail = (
                        "Your subscription is inactive. Please complete payment to activate."
                        if sub_status == "INACTIVE"
                        else "No active subscription. Please subscribe to continue."
                    )
                    return JsonResponse(
                        {
                            "detail": detail,
                            "subscription_status": sub_status,
                            "code": code,
                        },
                        status=402,
                    )

            is_exempt = any(
                request.path.startswith(prefix)
                for prefix in _SOFT_BLOCK_EXEMPT_PREFIXES
            )

            if not is_exempt:
                # Soft-block: EXPIRED/CANCELLED blocks writes only
                if (
                    sub_status in _SOFT_BLOCKED_STATUSES
                    and request.method in _WRITE_METHODS
                ):
                    from django.http import JsonResponse

                    return JsonResponse(
                        {
                            "detail": (
                                "Your subscription has expired. "
                                "Please upgrade your plan to continue "
                                "using this feature."
                            ),
                            "subscription_status": sub_status,
                            "code": "subscription_expired",
                        },
                        status=402,
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
