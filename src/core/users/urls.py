from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PatientViewSet, RegisterView, UserProfileView

router = DefaultRouter()
router.register(r'patients', PatientViewSet, basename='patient')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('', include(router.urls)),
]
