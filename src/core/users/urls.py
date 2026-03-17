from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PatientViewSet,
    RegisterView,
    UserProfileView,
)

router = DefaultRouter()
router.register(r"patients", PatientViewSet, basename="patient")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path(
        "password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("", include(router.urls)),
]
