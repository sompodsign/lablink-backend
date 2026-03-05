import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.tenants.permissions import IsCenterStaff, IsCenterStaffOrDoctor
from core.users.serializers import (
    PatientRegistrationSerializer,
    PatientSerializer,
    UserSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PatientViewSet(viewsets.ModelViewSet):
    """
    Patient management endpoint. Staff register walk-in patients and manage profiles.
    Scoped strictly to the current tenant center.
    """

    permission_classes = [permissions.IsAuthenticated, IsCenterStaff]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        tenant = self.request.tenant
        # Patients who either registered at this center or have appointments here
        return (
            User.objects.filter(
                Q(patient_profile__registered_at_center=tenant)
                | Q(appointments__center=tenant)
            )
            .prefetch_related('patient_profile')
            .distinct()
            .order_by('first_name', 'last_name')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return PatientRegistrationSerializer
        return PatientSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        return [permissions.IsAuthenticated(), IsCenterStaff()]

    def create(self, request, *args, **kwargs):
        serializer = PatientRegistrationSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            PatientSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )
