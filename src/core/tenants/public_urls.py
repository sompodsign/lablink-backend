from django.urls import path

from .public_views import PublicBookView, PublicCenterView, PublicDoctorsView

urlpatterns = [
    path("center/", PublicCenterView.as_view(), name="public-center"),
    path("doctors/", PublicDoctorsView.as_view(), name="public-doctors"),
    path("book/", PublicBookView.as_view(), name="public-book"),
]
