import logging
from datetime import date as dt_date

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.appointments.models import Appointment
from core.tenants.models import DiagnosticCenter, Doctor
from core.tenants.serializers import DiagnosticCenterSerializer, DoctorSerializer
from core.tenants.throttles import CenterBookingThrottle

logger = logging.getLogger(__name__)


class PublicCenterView(APIView):
    """Public: returns center info by domain."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        domain = request.query_params.get("domain", "").strip().lower()
        if not domain:
            return Response(
                {"detail": "domain query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            center = DiagnosticCenter.objects.get(domain=domain, is_active=True)
        except DiagnosticCenter.DoesNotExist:
            return Response(
                {"detail": "Center not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            DiagnosticCenterSerializer(center, context={"request": request}).data
        )


class PublicDoctorsView(APIView):
    """Public: returns doctors list for a center by domain."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        domain = request.query_params.get("domain", "").strip().lower()
        if not domain:
            return Response(
                {"detail": "domain query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            center = DiagnosticCenter.objects.get(domain=domain, is_active=True)
        except DiagnosticCenter.DoesNotExist:
            return Response(
                {"detail": "Center not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        doctors = Doctor.objects.filter(user__center=center)
        return Response(DoctorSerializer(doctors, many=True).data)


class PublicBookView(APIView):
    """Public: guest appointment booking with per-center rate limiting."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [CenterBookingThrottle]

    def post(self, request):
        data = request.data
        domain = (data.get("domain") or "").strip().lower()
        if not domain:
            return Response(
                {"detail": "domain is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve center
        try:
            center = DiagnosticCenter.objects.get(domain=domain, is_active=True)
        except DiagnosticCenter.DoesNotExist:
            return Response(
                {"detail": "Center not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if online appointments are enabled
        if not center.allow_online_appointments:
            return Response(
                {"detail": "Online appointments are not available for this center."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate required fields
        guest_name = (data.get("guest_name") or "").strip()
        guest_phone = (data.get("guest_phone") or "").strip()
        date_str = data.get("date")
        time_str = data.get("time")

        errors = {}
        if not guest_name:
            errors["guest_name"] = ["This field is required."]
        if not guest_phone:
            errors["guest_phone"] = ["This field is required."]
        if not date_str:
            errors["date"] = ["This field is required."]
        if not time_str:
            errors["time"] = ["This field is required."]
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Validate date
        from datetime import datetime

        try:
            date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return Response(
                {"date": ["Invalid date format. Use YYYY-MM-DD."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if date_val < dt_date.today():
            return Response(
                {"date": ["Cannot book an appointment in the past."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate time
        try:
            time_val = datetime.strptime(time_str, "%H:%M").time()
        except (ValueError, TypeError):
            return Response(
                {"time": ["Invalid time format. Use HH:MM."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate doctor (optional)
        doctor = None
        doctor_id = data.get("doctor")
        if doctor_id:
            try:
                doctor = Doctor.objects.get(pk=int(doctor_id), user__center=center)
            except (Doctor.DoesNotExist, ValueError, TypeError):
                return Response(
                    {"doctor": ["Doctor not found at this center."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        symptoms = data.get("symptoms", "")

        # Auto-link: if exactly one user with matching phone + name exists
        # at this center, link the appointment to them.
        # (Phone alone is not unique — families share numbers.)
        from django.contrib.auth import get_user_model
        from django.db.models import Value
        from django.db.models.functions import Concat

        User = get_user_model()
        matched_user = None
        if guest_phone:
            candidates = (
                User.objects.filter(phone_number=guest_phone, center=center)
                .annotate(full_name=Concat("first_name", Value(" "), "last_name"))
                .filter(full_name__iexact=guest_name)
            )
            if candidates.count() == 1:
                matched_user = candidates.first()

        appointment = Appointment.objects.create(
            patient=matched_user,
            center=center,
            doctor=doctor,
            date=date_val,
            time=time_val,
            status="PENDING",
            symptoms=symptoms,
            guest_name=guest_name,
            guest_phone=guest_phone,
        )

        logger.info(
            "Public booking created: id=%s center=%s guest=%s",
            appointment.id,
            center.domain,
            guest_name,
        )

        return Response(
            {
                "detail": "Appointment booked successfully! "
                "The center will confirm it shortly.",
                "id": appointment.id,
            },
            status=status.HTTP_201_CREATED,
        )
