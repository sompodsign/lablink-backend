from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from core.users.views import CustomTokenObtainView

urlpatterns = [
    path("admin/", admin.site.urls),
    # App APIs
    path("api/tenants/", include("core.tenants.urls")),
    path("api/public/", include("core.tenants.public_urls")),
    path("api/diagnostics/", include("apps.diagnostics.urls")),
    path("api/appointments/", include("apps.appointments.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/subscriptions/", include("apps.subscriptions.urls")),
    # Auth
    path("api/auth/", include("core.users.urls")),
    path("api/token/", CustomTokenObtainView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # API Documentation (drf-spectacular)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"
    ),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
