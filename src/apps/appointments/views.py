import logging
from datetime import date

from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.tenants.permissions import IsCenterDoctor, IsCenterStaffOrDoctor

from .models import Appointment
from .serializers import AppointmentSerializer, ConsultationUpdateSerializer

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        tags=['Appointments'],
        summary='List appointments',
        description=(
            'Returns appointments for the current center.\n\n'
            '- **Doctors** see only their own appointments.\n'
            '- **Staff** see all appointments at the center.\n'
            '- **Patients** see only their own appointments.'
        ),
    ),
    retrieve=extend_schema(
        tags=['Appointments'],
        summary='Get appointment detail',
    ),
    create=extend_schema(
        tags=['Appointments'],
        summary='Create an appointment',
        description=(
            'Staff or doctor schedules a new appointment. '
            'The `center` should match the current tenant. '
            'The `patient` must be a registered user.'
        ),
        examples=[
            OpenApiExample(
                'Schedule appointment',
                value={
                    'patient': 5,
                    'center': 1,
                    'doctor': 2,
                    'date': '2026-03-10',
                    'time': '10:30',
                    'symptoms': 'Persistent headache for 3 days',
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=['Appointments'],
        summary='Update an appointment',
        description='Staff can update appointment status, date, time, or reassign doctor.',
    ),
    destroy=extend_schema(
        tags=['Appointments'],
        summary='Cancel an appointment',
    ),
)
class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        tenant = self.request.tenant

        qs = Appointment.objects.filter(center=tenant).select_related(
            'patient', 'center', 'doctor__user'
        )

        if hasattr(user, 'doctor_profile'):
            qs = qs.filter(doctor=user.doctor_profile)
        elif hasattr(user, 'staff_profile'):
            pass  # staff see all
        else:
            qs = qs.filter(patient=user)

        params = self.request.query_params
        if patient_id := params.get('patient'):
            qs = qs.filter(patient_id=patient_id)
        if status_val := params.get('status'):
            qs = qs.filter(status=status_val)
        if date_val := params.get('date'):
            qs = qs.filter(date=date_val)

        ordering = params.get('ordering', '-date')
        allowed = {
            'date', '-date', 'time', '-time',
            'status', '-status',
        }
        if ordering in allowed:
            qs = qs.order_by(ordering)

        return qs

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        if self.action == 'consult':
            return [permissions.IsAuthenticated(), IsCenterDoctor()]
        if self.action == 'today':
            return [permissions.IsAuthenticated(), IsCenterDoctor()]
        return [permissions.IsAuthenticated()]

    @extend_schema(
        tags=['Appointments'],
        summary="Today's appointments (doctor only)",
        description=(
            "Returns today's appointments for the logged-in doctor at the current center, "
            "ordered by time. Useful for the doctor's daily consultation dashboard."
        ),
        responses={200: AppointmentSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='today')
    def today(self, request):
        today_date = date.today()
        qs = self.get_queryset().filter(date=today_date).order_by('time')
        serializer = AppointmentSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Appointments'],
        summary='Add consultation notes (doctor only)',
        description=(
            'Doctor updates an appointment with clinical notes, symptoms, '
            'or changes the appointment status (e.g., to `COMPLETED`).'
        ),
        request=ConsultationUpdateSerializer,
        responses={200: AppointmentSerializer},
        examples=[
            OpenApiExample(
                'Add symptoms and complete',
                value={
                    'symptoms': 'Fever for 3 days, body ache, loss of appetite.',
                    'status': 'COMPLETED',
                },
                request_only=True,
            ),
        ],
    )
    @action(detail=True, methods=['patch'], url_path='consult')
    def consult(self, request, pk=None):
        appointment = self.get_object()
        serializer = ConsultationUpdateSerializer(
            appointment, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(
            'Consultation updated',
            extra={'appointment_id': appointment.id, 'doctor_id': request.user.id},
        )
        return Response(AppointmentSerializer(appointment).data)
