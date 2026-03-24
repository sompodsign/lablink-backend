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


class ResendNotificationThrottle(SimpleRateThrottle):
    """
    Rate-limits resend-email / resend-sms to 3 per hour per user per report.
    Prevents spamming patients with repeated notifications.
    """

    scope = "resend_notification"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        report_pk = view.kwargs.get("pk", "0")
        return f"throttle_resend_{request.user.pk}_{report_pk}"
