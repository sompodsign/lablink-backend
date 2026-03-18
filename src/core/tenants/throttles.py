from rest_framework.throttling import SimpleRateThrottle


class CenterBookingThrottle(SimpleRateThrottle):
    """
    Rate-limits public appointment bookings per IP + center domain.
    Each visitor gets 20 bookings/hour per center — spamming one center
    does not affect their quota at another.
    """

    scope = "public_booking"

    def get_cache_key(self, request, view):
        domain = request.data.get("domain", "unknown")
        ident = self.get_ident(request)
        return f"throttle_public_booking_{ident}_{domain}"
