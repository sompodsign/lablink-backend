
from django.db import models


class TenantQuerySetMixin:
    """
    Mixin for QuerySets to automatically filter by the current tenant.
    Usage: Add to a custom manager's queryset.
    """

    def for_tenant(self, tenant):
        """Filter queryset by tenant (DiagnosticCenter)."""
        if hasattr(self.model, 'center'):
            return self.filter(center=tenant)
        elif hasattr(self.model, 'diagnostic_center'):
            return self.filter(diagnostic_center=tenant)
        return self


class TenantManager(models.Manager):
    """Manager that provides tenant-scoped queries."""

    def for_tenant(self, tenant):
        return self.get_queryset().for_tenant(tenant)


class TenantModelMixin(models.Model):
    """
    Abstract model mixin for tenant-scoped models.
    Subclasses should have a 'center' ForeignKey to DiagnosticCenter.
    """

    class Meta:
        abstract = True
