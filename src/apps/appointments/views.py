import logging
from datetime import date, datetime, timedelta

from django.db.models import Q
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.notifications.emails import EmailType, send_email_async
from core.tenants.permissions import IsCenterDoctor, IsCenterStaffOrDoctor

from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    ConsultationUpdateSerializer,
    PatientBookingSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        tags=["Appointments"],
        summary="List appointments",
        description=(
            "Returns appointments for the current center.\n\n"
            "- **Doctors** see only their own appointments.\n"
            "- **Staff** see all appointments at the center.\n"
            "- **Patients** see only their own appointments."
        ),
    ),
    retrieve=extend_schema(
        tags=["Appointments"],
        summary="Get appointment detail",
    ),
    create=extend_schema(
        tags=["Appointments"],
        summary="Create an appointment",
        description=(
            "Staff or doctor schedules a new appointment. "
            "The `center` should match the current tenant. "
            "The `patient` must be a registered user."
        ),
        examples=[
            OpenApiExample(
                "Schedule appointment",
                value={
                    "patient": 5,
                    "center": 1,
                    "doctor": 2,
                    "date": "2026-03-10",
                    "time": "10:30",
                    "symptoms": "Persistent headache for 3 days",
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=["Appointments"],
        summary="Update an appointment",
        description="Staff can update appointment status, date, time, or reassign doctor.",
    ),
    destroy=extend_schema(
        tags=["Appointments"],
        summary="Cancel an appointment",
    ),
)
class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        tenant = self.request.tenant

        qs = (
            Appointment.objects.filter(center=tenant)
            .select_related("patient", "center", "doctor__user")
            .prefetch_related("invoices")
        )

        from core.tenants.models import Doctor, Staff

        if Doctor.objects.filter(user=user, user__center=tenant).exists():
            qs = qs.filter(doctor__user=user)
        elif Staff.objects.filter(user=user, center=tenant).exists():
            pass  # staff see all
        else:
            qs = qs.filter(patient=user)

        params = self.request.query_params
        if patient_id := params.get("patient"):
            qs = qs.filter(patient_id=patient_id)
        if status_val := params.get("status"):
            qs = qs.filter(status=status_val)
        if date_val := params.get("date"):
            qs = qs.filter(date=date_val)
        if doctor_val := params.get("doctor"):
            qs = qs.filter(doctor_id=doctor_val)
        if search := params.get("search", "").strip():
            qs = qs.filter(
                Q(patient__first_name__icontains=search)
                | Q(patient__last_name__icontains=search)
                | Q(patient__phone_number__icontains=search)
                | Q(guest_name__icontains=search)
            )

        ordering = params.get("ordering", "-created_at")
        allowed = {
            "date",
            "-date",
            "time",
            "-time",
            "status",
            "-status",
            "created_at",
            "-created_at",
        }
        if ordering in allowed:
            qs = qs.order_by(ordering)

        return qs

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        if self.action == "consult":
            return [permissions.IsAuthenticated(), IsCenterDoctor()]
        if self.action == "today":
            return [permissions.IsAuthenticated(), IsCenterDoctor()]
        if self.action in ("mark_paid",):
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        if self.action == "available_slots":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    # ── Available Slots ────────────────────────────────────────────
    @extend_schema(
        tags=["Appointments"],
        summary="Get available time slots",
        description=(
            "Returns available time slots for a given doctor and date. "
            "Pass `doctor` (id) and `date` (YYYY-MM-DD) as query params. "
            "For public (unauthenticated) access, also pass `domain`."
        ),
    )
    @action(detail=False, methods=["get"], url_path="available-slots")
    def available_slots(self, request):
        from core.tenants.models import DiagnosticCenter, Doctor

        doctor_id = request.query_params.get("doctor")
        date_str = request.query_params.get("date")

        if not doctor_id or not date_str:
            return Response(
                {"detail": "Both doctor and date are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            slot_date = date.fromisoformat(date_str)
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve the center — from auth or from domain param
        domain = request.query_params.get("domain")
        if domain:
            try:
                center = DiagnosticCenter.objects.get(
                    domain=domain,
                    is_active=True,
                )
            except DiagnosticCenter.DoesNotExist:
                return Response(
                    {"detail": "Center not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        elif hasattr(request, "tenant") and request.tenant:
            center = request.tenant
        else:
            return Response(
                {"detail": "domain query param is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            doctor = Doctor.objects.get(id=doctor_id, user__center=center)
        except Doctor.DoesNotExist:
            return Response(
                {"detail": "Doctor not found at this center."},
                status=status.HTTP_404_NOT_FOUND,
            )

        slots = self._generate_slots(doctor, slot_date, center)
        return Response({"slots": slots})

    @staticmethod
    def _generate_slots(doctor, slot_date, center):
        """Build time-slot list; mark booked ones as unavailable."""
        start = doctor.available_from
        end = doctor.available_to
        duration = doctor.slot_duration_minutes or 30

        # Existing non-cancelled appointments for this doctor+date
        booked_times = set(
            Appointment.objects.filter(
                doctor=doctor,
                center=center,
                date=slot_date,
            )
            .exclude(status="CANCELLED")
            .values_list("time", flat=True)
        )

        slots = []
        current = datetime.combine(slot_date, start)
        end_dt = datetime.combine(slot_date, end)

        while current < end_dt:
            t = current.time()
            slots.append(
                {
                    "time": t.strftime("%H:%M"),
                    "available": t not in booked_times,
                }
            )
            current += timedelta(minutes=duration)

        return slots

    def perform_update(self, serializer):
        """Auto-create/cancel invoice when appointment status changes."""
        old_status = serializer.instance.status
        appointment = serializer.save()
        new_status = appointment.status

        if old_status != "COMPLETED" and new_status == "COMPLETED":
            self._auto_create_invoice(appointment)
        elif old_status == "COMPLETED" and new_status != "COMPLETED":
            self._cancel_invoice(appointment)

    def _cancel_invoice(self, appointment):
        """Cancel the linked invoice when appointment is un-completed."""
        from apps.payments.models import Invoice

        for invoice in appointment.invoices.exclude(status=Invoice.Status.CANCELLED):
            invoice.status = Invoice.Status.CANCELLED
            invoice.save(update_fields=["status"])
            logger.info(
                "Cancelled invoice %s — appointment %s moved away from COMPLETED",
                invoice.invoice_number,
                appointment.id,
            )

    def _auto_create_invoice(self, appointment):
        """Create an ISSUED invoice with the doctor's visit fee."""
        from apps.payments.models import Invoice, InvoiceItem

        # Skip if a non-cancelled invoice already exists
        if appointment.invoices.exclude(status=Invoice.Status.CANCELLED).exists():
            return

        invoice = Invoice.objects.create(
            patient=appointment.patient,
            walk_in_name=appointment.guest_name or "",
            walk_in_phone=appointment.guest_phone or "",
            center=appointment.center,
            appointment=appointment,
            discount_percentage=0,
            notes="Auto-generated on appointment completion",
            created_by=self.request.user,
            status=Invoice.Status.PAID,
        )

        # Add visit fee if doctor is assigned
        if appointment.doctor and appointment.doctor.visit_fee > 0:
            InvoiceItem.objects.create(
                invoice=invoice,
                item_type=InvoiceItem.ItemType.VISIT_FEE,
                description=f"Consultation Fee — {appointment.doctor}",
                quantity=1,
                unit_price=appointment.doctor.visit_fee,
            )

        invoice.recalculate_totals()
        logger.info(
            "Auto-created invoice %s for appointment %s",
            invoice.invoice_number,
            appointment.id,
        )

    @extend_schema(
        tags=["Appointments"],
        summary="Today's appointments (doctor only)",
        description=(
            "Returns today's appointments for the logged-in doctor at the current center, "
            "ordered by time. Useful for the doctor's daily consultation dashboard."
        ),
        responses={200: AppointmentSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="today")
    def today(self, request):
        today_date = date.today()
        qs = self.get_queryset().filter(date=today_date).order_by("time")
        serializer = AppointmentSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Appointments"],
        summary="Add consultation notes (doctor only)",
        description=(
            "Doctor updates an appointment with clinical notes, symptoms, "
            "or changes the appointment status (e.g., to `COMPLETED`)."
        ),
        request=ConsultationUpdateSerializer,
        responses={200: AppointmentSerializer},
        examples=[
            OpenApiExample(
                "Add symptoms and complete",
                value={
                    "symptoms": "Fever for 3 days, body ache, loss of appetite.",
                    "status": "COMPLETED",
                },
                request_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["patch"], url_path="consult")
    def consult(self, request, pk=None):
        appointment = self.get_object()
        serializer = ConsultationUpdateSerializer(
            appointment, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(
            "Consultation updated",
            extra={"appointment_id": appointment.id, "doctor_id": request.user.id},
        )
        return Response(AppointmentSerializer(appointment).data)

    @extend_schema(
        tags=["Appointments"],
        summary="Mark appointment as paid",
        description="Sets the linked invoice status to PAID.",
        responses={200: AppointmentSerializer},
    )
    @action(detail=True, methods=["patch"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        appointment = self.get_object()
        invoice = appointment.invoices.first()
        if not invoice:
            return Response(
                {"detail": "No invoice linked to this appointment."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = "PAID"
        invoice.save(update_fields=["status"])
        logger.info(
            "Invoice %s marked as PAID for appointment %s",
            invoice.invoice_number,
            appointment.id,
        )
        # Refresh prefetch cache
        appointment = self.get_object()
        return Response(AppointmentSerializer(appointment).data)

    @extend_schema(
        tags=["Appointments"],
        summary="Patient books an appointment online",
        description=(
            "Authenticated patient self-books an appointment at the current center. "
            "Requires `allow_online_appointments` to be enabled on the center. "
            "Booking is created with status PENDING until confirmed by staff."
        ),
        request=PatientBookingSerializer,
        responses={
            201: AppointmentSerializer,
            403: {"description": "Online appointments not enabled"},
        },
    )
    @action(detail=False, methods=["post"], url_path="book")
    def book(self, request):
        tenant = request.tenant
        if not tenant.allow_online_appointments:
            return Response(
                {
                    "detail": "Online appointment booking is not enabled for this center."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Auto-create PatientProfile if user doesn't have one
        from core.users.models import PatientProfile

        PatientProfile.objects.get_or_create(
            user=request.user,
            defaults={"registered_at_center": tenant},
        )

        serializer = PatientBookingSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        appointment = serializer.save()
        logger.info(
            "Patient booked appointment online",
            extra={
                "appointment_id": appointment.id,
                "patient_id": request.user.id,
                "center_id": tenant.id,
            },
        )

        # Send booking confirmation email
        patient_email = request.user.email
        if patient_email:
            doctor_name = (
                appointment.doctor.user.get_full_name()
                if appointment.doctor
                else "To be assigned"
            )
            send_email_async(
                EmailType.APPOINTMENT_BOOKED,
                recipient=patient_email,
                context={
                    "patient_name": request.user.get_full_name(),
                    "center_name": tenant.name,
                    "doctor_name": doctor_name,
                    "date": str(appointment.date),
                    "time": str(appointment.time),
                },
            )

        return Response(
            AppointmentSerializer(appointment).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        appointment = self.get_object()
        old_status = appointment.status
        response = super().partial_update(request, *args, **kwargs)
        appointment.refresh_from_db()
        new_status = appointment.status

        # Send email on status change
        if (
            old_status != new_status
            and appointment.patient
            and appointment.patient.email
        ):
            patient_email = appointment.patient.email
            doctor_name = (
                appointment.doctor.user.get_full_name() if appointment.doctor else "N/A"
            )
            ctx = {
                "patient_name": appointment.patient.get_full_name(),
                "center_name": appointment.center.name,
                "doctor_name": doctor_name,
                "date": str(appointment.date),
                "time": str(appointment.time),
            }

            if new_status == "CONFIRMED":
                send_email_async(EmailType.APPOINTMENT_CONFIRMED, patient_email, ctx)
            elif new_status == "CANCELLED":
                send_email_async(EmailType.APPOINTMENT_CANCELLED, patient_email, ctx)

        return response
