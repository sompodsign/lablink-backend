import logging

from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.tenants.permissions import IsCenterStaff, IsCenterStaffOrDoctor
from core.users.serializers import (
    PatientRegistrationSerializer,
    PatientSerializer,
    UserSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)

APPROVAL_MESSAGES = {
    User.ApprovalStatus.PENDING: 'Your account is pending admin approval. Please wait for activation.',
    User.ApprovalStatus.DECLINED: 'Your account request has been declined. Please contact the administrator.',
}


@extend_schema(
    tags=['Authentication'],
    summary='Obtain JWT token pair',
    description='Authenticate with username or email and password.',
)
class CustomTokenObtainView(APIView):
    """Custom login that checks approval_status before issuing tokens."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username', '')
        password = request.data.get('password', '')

        if not username or not password:
            return Response(
                {'detail': 'Username and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)

        if user is None:
            # Check if user exists but has approval issue
            try:
                lookup = User.objects.get(
                    Q(username=username) | Q(email=username),
                )
            except User.DoesNotExist:
                return Response(
                    {'detail': 'Invalid credentials.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # User exists — check approval status
            if lookup.approval_status != User.ApprovalStatus.APPROVED:
                msg = APPROVAL_MESSAGES.get(
                    lookup.approval_status,
                    'Account access denied.',
                )
                return Response(
                    {
                        'detail': msg,
                        'approval_status': lookup.approval_status,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if not lookup.is_active:
                return Response(
                    {
                        'detail': 'Your account has been deactivated by an administrator.',
                        'approval_status': 'DEACTIVATED',
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Wrong password
            return Response(
                {'detail': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # User authenticated — check approval status
        if user.approval_status != User.ApprovalStatus.APPROVED:
            msg = APPROVAL_MESSAGES.get(
                user.approval_status, 'Account access denied.',
            )
            return Response(
                {
                    'detail': msg,
                    'approval_status': user.approval_status,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Issue tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


@extend_schema(
    tags=['Authentication'],
    summary='Register a new user account',
    description=(
        'Create a new user account with username and password. '
        'This creates a generic user — not a patient, doctor, or staff member. '
        'Use `/api/auth/patients/` to register patients.'
    ),
    examples=[
        OpenApiExample(
            'Register user',
            value={
                'username': 'johndoe',
                'email': 'john@example.com',
                'password': 'securepass123',
                'first_name': 'John',
                'last_name': 'Doe',
                'phone_number': '01712345678',
            },
            request_only=True,
        ),
    ],
)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(tags=['Authentication'])
class UserProfileView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the currently authenticated user's profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema_view(
    list=extend_schema(
        tags=['Patients'],
        summary='List patients',
        description=(
            'Returns patients registered at or with appointments at the current center. '
            'Accessible by staff and doctors.'
        ),
    ),
    retrieve=extend_schema(
        tags=['Patients'],
        summary='Get patient detail',
        description='Retrieve a single patient profile with medical history.',
    ),
    create=extend_schema(
        tags=['Patients'],
        summary='Register a walk-in patient',
        description=(
            'Staff registers a new patient at the current center. '
            'Creates a `User` (without login credentials) and a `PatientProfile` '
            'linked to this center. The patient can later be upgraded to a full account.'
        ),
        request=PatientRegistrationSerializer,
        responses={201: PatientSerializer},
        examples=[
            OpenApiExample(
                'Register walk-in patient',
                value={
                    'first_name': 'Fatima',
                    'last_name': 'Khan',
                    'phone_number': '01700000099',
                    'blood_group': 'B+',
                    'date_of_birth': '1990-05-15',
                    'address': '12/A Dhanmondi, Dhaka',
                    'emergency_contact_name': 'Karim Khan',
                    'emergency_contact_phone': '01800000088',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Minimal registration',
                value={
                    'first_name': 'Rahim',
                    'last_name': 'Uddin',
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=['Patients'],
        summary='Update patient info',
        description='Staff updates patient profile (name, phone, medical history, etc.).',
    ),
)
class PatientViewSet(viewsets.ModelViewSet):
    """
    Patient management endpoint. Staff register walk-in patients and manage profiles.
    Scoped strictly to the current tenant center.
    """

    permission_classes = [permissions.IsAuthenticated, IsCenterStaff]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        tenant = self.request.tenant
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
        if self.action in ('list', 'retrieve', 'create'):
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
