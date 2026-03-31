"""URL configuration for the AI app."""

from django.urls import path

from .views import ReportExtractionView

urlpatterns = [
    path(
        'extract-report/',
        ReportExtractionView.as_view(),
        name='ai-extract-report',
    ),
]
