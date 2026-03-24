import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.emails import EmailType, send_email
from core.tenants.permissions import (
    HasCenterPermission,
    IsCenterStaff,
    IsCenterStaffOrDoctor,
)
from core.users.serializers import (
    PatientRegistrationSerializer,
    PatientSerializer,
    UserSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)

APPROVAL_MESSAGES = {
    User.ApprovalStatus.PENDING: "Your account is pending admin approval. Please wait for activation.",
    User.ApprovalStatus.DECLINED: "Your account request has been declined. Please contact the administrator.",
}


def _resolve_center_from_request(request):
    """Resolve DiagnosticCenter from the request Origin header subdomain.

    Returns None for main domain requests (no subdomain).
    """
    from urllib.parse import urlparse

    from core.tenants.models import DiagnosticCenter

    origin = request.META.get("HTTP_ORIGIN", "")
    if not origin:
        # Fallback to Host header
        origin = request.META.get("HTTP_HOST", "")
        if origin:
            origin = f"http://{origin}"

    if not origin:
        return None

    hostname = urlparse(origin).hostname or ""
    parts = hostname.split(".")
    if len(parts) > 1:
        subdomain = parts[0]
        return DiagnosticCenter.objects.filter(
            domain=subdomain,
        ).first()

    return None


@extend_schema(
    tags=["Authentication"],
    summary="Obtain JWT token pair",
    description="Authenticate with username or email and password.",
)
class CustomTokenObtainView(APIView):
    """Custom login scoped to the center resolved from the request origin."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("username", "")  # frontend sends email as "username"
        password = request.data.get("password", "")

        if not email or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve center from request origin (subdomain)
        center = _resolve_center_from_request(request)

        # Build user lookup scoped to center (supports username, email, or phone)
        identifier_q = Q(email=email) | Q(username=email) | Q(phone_number=email)
        if center:
            lookup_qs = User.objects.filter(identifier_q, center=center)
        else:
            # Main domain — only superadmins (center=NULL)
            lookup_qs = User.objects.filter(
                identifier_q,
                center__isnull=True,
                is_superuser=True,
            )

        # Phone numbers may be shared by family — try password against each
        users = list(lookup_qs)
        if not users:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user_record = None
        for candidate in users:
            if candidate.check_password(password):
                user_record = candidate
                break

        if user_record is None:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Check approval status
        if user_record.approval_status != User.ApprovalStatus.APPROVED:
            msg = APPROVAL_MESSAGES.get(
                user_record.approval_status,
                "Account access denied.",
            )
            return Response(
                {
                    "detail": msg,
                    "approval_status": user_record.approval_status,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user_record.is_active:
            return Response(
                {
                    "detail": "Your account has been deactivated by an administrator.",
                    "approval_status": "DEACTIVATED",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # (Password already verified during lookup above)

        # Check if center is deactivated (superadmins bypass)
        if center and not center.is_active and not user_record.is_superuser:
            return Response(
                {
                    "detail": (
                        "Your diagnostic center has been deactivated. "
                        "Please contact the platform administrator."
                    ),
                    "approval_status": "CENTER_DEACTIVATED",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Issue tokens
        refresh = RefreshToken.for_user(user_record)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )


@extend_schema(
    tags=["Authentication"],
    summary="Request password reset",
    description="Send a password reset link to the user's email.",
)
class PasswordResetRequestView(APIView):
    """Accept email, generate token, send reset link."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        if not email:
            return Response(
                {"detail": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Always return success to avoid email enumeration
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {
                    "detail": "If an account with that email exists, a reset link has been sent."
                },
            )

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Build frontend reset URL from request origin (subdomain-aware)
        origin = request.META.get("HTTP_ORIGIN", "")
        if not origin:
            host = request.get_host()
            scheme = "https" if request.is_secure() else "http"
            origin = f"{scheme}://{host}"
        # Strip /api suffix if present (origin should be the frontend root)
        frontend_base = origin.rstrip("/")
        if frontend_base.startswith("https://api."):
            # Request came from api.lablink.bd — fallback to main domain
            frontend_base = frontend_base.replace("https://api.", "https://", 1)
        reset_url = f"{frontend_base}/reset-password/{uid}/{token}"

        logger.info("Password reset URL generated for %s", user.email)

        send_email(
            EmailType.PASSWORD_RESET,
            recipient=user.email,
            context={
                "user_name": user.get_full_name() or user.username,
                "reset_url": reset_url,
            },
        )
        return Response(
            {
                "detail": "If an account with that email exists, a reset link has been sent."
            },
        )


@extend_schema(
    tags=["Authentication"],
    summary="Confirm password reset",
    description="Set a new password using the uid and token from the reset link.",
)
class PasswordResetConfirmView(APIView):
    """Validate uid/token and set new password."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uid = request.data.get("uid", "")
        token = request.data.get("token", "")
        new_password = request.data.get("new_password", "")

        if not all([uid, token, new_password]):
            return Response(
                {"detail": "uid, token, and new_password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            logger.warning(
                "Password reset: invalid uid=%s",
                uid,
            )
            return Response(
                {"detail": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_valid = default_token_generator.check_token(user, token)
        logger.info(
            "Password reset attempt: user=%s uid=%s token_valid=%s last_login=%s",
            user.username,
            uid,
            token_valid,
            user.last_login,
        )

        if not token_valid:
            return Response(
                {"detail": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()
        logger.info("Password reset completed for user %s", user.username)

        if user.email:
            send_email(
                EmailType.PASSWORD_RESET_SUCCESS,
                recipient=user.email,
                context={"user_name": user.get_full_name() or user.username},
            )

        return Response(
            {"detail": "Password has been reset successfully. You can now log in."},
        )


@extend_schema(
    tags=["Authentication"],
    summary="Register a new user account",
    description=(
        "Create a new user account with username and password. "
        "This creates a generic user — not a patient, doctor, or staff member. "
        "Use `/api/auth/patients/` to register patients."
    ),
    examples=[
        OpenApiExample(
            "Register user",
            value={
                "username": "johndoe",
                "email": "john@example.com",
                "password": "securepass123",
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "01712345678",
            },
            request_only=True,
        ),
    ],
)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        center = _resolve_center_from_request(self.request)
        center_name = center.name if center else "LabLink"

        # Build login URL from request origin
        origin = self.request.META.get("HTTP_ORIGIN", "")
        if not origin:
            host = self.request.get_host()
            scheme = "https" if self.request.is_secure() else "http"
            origin = f"{scheme}://{host}"
        login_url = f"{origin.rstrip('/')}/login"

        if user.email:
            send_email(
                EmailType.WELCOME_PATIENT,
                recipient=user.email,
                context={
                    "patient_name": user.get_full_name() or user.username,
                    "center_name": center_name,
                    "login_url": login_url,
                },
            )


@extend_schema(tags=["Authentication"])
class UserProfileView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the currently authenticated user's profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=["Authentication"],
    summary="Change password",
    description="Change the authenticated user's password. Requires current password.",
)
class ChangePasswordView(APIView):
    """Authenticated user changes their own password."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current_password = request.data.get("current_password", "")
        new_password = request.data.get("new_password", "")
        confirm_password = request.data.get("confirm_password", "")

        if not all([current_password, new_password, confirm_password]):
            return Response(
                {"detail": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {"detail": "New passwords do not match."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not request.user.check_password(current_password):
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate Django password rules
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            validate_password(new_password, request.user)
        except DjangoValidationError as e:
            return Response(
                {"detail": e.messages[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new_password)
        request.user.save()
        logger.info("User %s changed password", request.user.username)

        return Response({"detail": "Password changed successfully."})


@extend_schema_view(
    list=extend_schema(
        tags=["Patients"],
        summary="List patients",
        description=(
            "Returns patients registered at or with appointments at the current center. "
            "Accessible by staff and doctors."
        ),
    ),
    retrieve=extend_schema(
        tags=["Patients"],
        summary="Get patient detail",
        description="Retrieve a single patient profile with medical history.",
    ),
    create=extend_schema(
        tags=["Patients"],
        summary="Register a walk-in patient",
        description=(
            "Staff registers a new patient at the current center. "
            "Creates a `User` (without login credentials) and a `PatientProfile` "
            "linked to this center. The patient can later be upgraded to a full account."
        ),
        request=PatientRegistrationSerializer,
        responses={201: PatientSerializer},
        examples=[
            OpenApiExample(
                "Register walk-in patient",
                value={
                    "first_name": "Fatima",
                    "last_name": "Khan",
                    "phone_number": "01700000099",
                    "blood_group": "B+",
                    "date_of_birth": "1990-05-15",
                    "address": "12/A Dhanmondi, Dhaka",
                    "emergency_contact_name": "Karim Khan",
                    "emergency_contact_phone": "01800000088",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Minimal registration",
                value={
                    "first_name": "Rahim",
                    "last_name": "Uddin",
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=["Patients"],
        summary="Update patient info",
        description=(
            "Staff with `manage_patients` permission updates patient profile "
            "(name, phone, medical history, etc.)."
        ),
    ),
    destroy=extend_schema(
        tags=["Patients"],
        summary="Delete a patient",
        description=(
            "Staff with `manage_patients` permission deletes a patient and their profile. "
            "This is a soft operation — only unpublished patients should be deleted."
        ),
    ),
)
class PatientViewSet(viewsets.ModelViewSet):
    """
    Patient management endpoint. Staff register walk-in patients and manage profiles.
    Scoped strictly to the current tenant center.
    """

    permission_classes = [permissions.IsAuthenticated, IsCenterStaff]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        tenant = self.request.tenant
        qs = (
            User.objects.filter(
                Q(patient_profile__registered_at_center=tenant)
                | Q(appointments__center=tenant)
            )
            .exclude(staff_profile__center=tenant)
            .exclude(doctor_profile__user__center=tenant)
            .prefetch_related("patient_profile")
            .distinct()
            .order_by("first_name", "last_name")
        )

        # Search filter for autocomplete
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone_number__icontains=search)
                | Q(email__icontains=search)
            )[:20]

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return PatientRegistrationSerializer
        return PatientSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "create"):
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        # update / partial_update / destroy require manage_patients
        perm = HasCenterPermission()
        perm.required_permission = "manage_patients"
        return [permissions.IsAuthenticated(), perm]

    def create(self, request, *args, **kwargs):
        serializer = PatientRegistrationSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            PatientSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )
