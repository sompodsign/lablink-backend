
from core.tenants.models import DiagnosticCenter


class TenantMiddleware:
    """
    Middleware to identify the current tenant from the request's Host header.
    Attaches the tenant (DiagnosticCenter) to request.tenant.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0]  # Remove port
        
        # Extract subdomain: e.g., "popularhospital.lablink.com.bd" -> "popularhospital"
        # For localhost development: "popularhospital.localhost" -> "popularhospital"
        parts = host.split('.')
        
        # Handle localhost development (e.g., demo.localhost)
        if 'localhost' in host or '127.0.0.1' in host:
            if len(parts) >= 2 and parts[0] not in ('localhost', '127'):
                subdomain = parts[0]
            else:
                subdomain = 'demo'  # Default for development
        else:
            # Production: first part is the subdomain
            subdomain = parts[0] if len(parts) > 2 else 'demo'

        try:
            request.tenant = DiagnosticCenter.objects.get(domain=subdomain)
        except DiagnosticCenter.DoesNotExist:
            # Fallback to first center or None for development
            request.tenant = DiagnosticCenter.objects.first()

        response = self.get_response(request)
        return response
