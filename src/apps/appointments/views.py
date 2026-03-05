import logging
from datetime import date

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.tenants.permissions import IsCenterDoctor, IsCenterStaff, IsCenterStaffOrDoctor

from .models import Appointment
from .serializers import AppointmentSerializer, ConsultationUpdateSerializer

logger = logging.getLogger(__name__)


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    Appointments are scoped to the current tenant center.
    - Doctors see only their own appointments.
    - Staff see all appointments for their center.
    - Patients see only their own appointments.
    """

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
            return qs.filter(doctor=user.doctor_profile)
        if hasattr(user, 'staff_profile'):
            return qs
        # Patient: only their own appointments
        return qs.filter(patient=user)

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsCenterStaffOrDoctor()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsCenterStaff()]
        if self.action == 'consult':
            return [permissions.IsAuthenticated(), IsCenterDoctor()]
        if self.action == 'today':
            return [permissions.IsAuthenticated(), IsCenterDoctor()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='today')
    def today(self, request):
        """Return today's appointments for the logged-in doctor."""
        today = date.today()
        qs = self.get_queryset().filter(date=today).order_by('time')
        serializer = AppointmentSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='consult')
    def consult(self, request, pk=None):
        """Doctor adds clinical notes/symptoms to an appointment."""
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
