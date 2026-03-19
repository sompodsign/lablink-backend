from django.urls import path

from apps.subscriptions.views import CenterRegistrationView, PublicPlanListView

from .public_views import (
    PublicBookView,
    PublicCenterView,
    PublicDoctorsView,
    PublicPlatformSettingsView,
)

urlpatterns = [
    path("center/", PublicCenterView.as_view(), name="public-center"),
    path("doctors/", PublicDoctorsView.as_view(), name="public-doctors"),
    path("book/", PublicBookView.as_view(), name="public-book"),
    path(
        "platform-settings/",
        PublicPlatformSettingsView.as_view(),
        name="public-platform-settings",
    ),
    path("plans/", PublicPlanListView.as_view(), name="public-plans"),
    path(
        "register-center/",
        CenterRegistrationView.as_view(),
        name="public-register-center",
    ),
]
