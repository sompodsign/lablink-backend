import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.tenants.permissions import IsCenterAdmin, IsCenterStaff

from .models import Doctor, Staff
from .serializers import (
    DiagnosticCenterSerializer,
    DoctorActivitySerializer,
    DoctorManagementSerializer,
    DoctorSerializer,
    StaffSerializer,
)

logger = logging.getLogger(__name__)


class CurrentTenantView(APIView):
    """
    Returns the current tenant (diagnostic center) based on the request domain.
    This is used by the frontend to load branding dynamically.
    """

    permission_classes = []  # Public endpoint

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if tenant:
            serializer = DiagnosticCenterSerializer(tenant, context={'request': request})
            return Response(serializer.data)
        return Response(
            {'error': 'No diagnostic center found for this domain'},
            status=status.HTTP_404_NOT_FOUND,
        )


class DoctorManagementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Staff manage doctors associated with their center.
    Admins can add/remove doctors from the center.
    """

    serializer_class = DoctorManagementSerializer

    def get_queryset(self):
        tenant = self.request.tenant
        return Doctor.objects.filter(centers=tenant).select_related('user').order_by(
            'user__first_name'
        )

    def get_permissions(self):
        if self.action == 'activity':
            return [permissions.IsAuthenticated(), IsCenterStaff()]
        return [permissions.IsAuthenticated(), IsCenterStaff()]

    @action(detail=True, methods=['post'], url_path='add-to-center')
    def add_to_center(self, request, pk=None):
        """Admin adds an existing doctor to this center."""
        if not IsCenterAdmin().has_permission(request, self):
            return Response(
                {'detail': 'Only admins can add doctors to the center.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            doctor = Doctor.objects.get(pk=pk)
        except Doctor.DoesNotExist:
            return Response({'detail': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        tenant = request.tenant
        doctor.centers.add(tenant)
        logger.info(
            'Doctor added to center',
            extra={'doctor_id': doctor.id, 'center_id': tenant.id},
        )
        return Response(DoctorManagementSerializer(doctor).data)

    @action(detail=True, methods=['post'], url_path='remove-from-center')
    def remove_from_center(self, request, pk=None):
        """Admin removes a doctor from this center (M2M removal only, not deletion)."""
        if not IsCenterAdmin().has_permission(request, self):
            return Response(
                {'detail': 'Only admins can remove doctors from the center.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        doctor = self.get_object()
        tenant = request.tenant
        doctor.centers.remove(tenant)
        logger.info(
            'Doctor removed from center',
            extra={'doctor_id': doctor.id, 'center_id': tenant.id},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='activity')
    def activity(self, request, pk=None):
        """Staff views a doctor's consultation history and prescribed tests at this center."""
        doctor = self.get_object()
        tenant = request.tenant

        appointments = doctor.appointments.filter(center=tenant).select_related('patient').order_by(
            '-date', '-time'
        )
        test_orders = doctor.user.ordered_tests.filter(center=tenant)

        recent = [
            {
                'id': a.id,
                'patient': a.patient.get_full_name(),
                'date': a.date.isoformat(),
                'status': a.status,
            }
            for a in appointments[:10]
        ]

        data = {
            'doctor': DoctorManagementSerializer(doctor).data,
            'total_appointments': appointments.count(),
            'total_test_orders': test_orders.count(),
            'recent_appointments': recent,
        }
        return Response(data)


class StaffViewSet(viewsets.ReadOnlyModelViewSet):
    """Staff listing for the current center (admin use)."""

    serializer_class = StaffSerializer
    permission_classes = [permissions.IsAuthenticated, IsCenterAdmin]

    def get_queryset(self):
        tenant = self.request.tenant
        return Staff.objects.filter(center=tenant).select_related('user')
