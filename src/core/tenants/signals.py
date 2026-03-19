"""
Signals for the tenants app.

Automatically creates default roles with permissions when a new
DiagnosticCenter is created.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from core.tenants.models import DiagnosticCenter, Permission, Role

logger = logging.getLogger(__name__)

# role_name → list of permission codenames (None = all permissions)
DEFAULT_ROLE_PERMS: dict[str, list[str] | None] = {
    "Admin": None,
    "Medical Technologist": [
        "view_patients",
        "view_reports",
        "create_reports",
        "manage_reports",
        "view_test_orders",
        "manage_test_orders",
    ],
    "Receptionist": [
        "view_patients",
        "manage_patients",
        "view_appointments",
        "manage_appointments",
        "view_reports",
        "view_payments",
        "manage_payments",
    ],
    "Doctor": [
        "view_patients",
        "view_appointments",
        "manage_appointments",
        "view_test_orders",
        "view_reports",
        "create_reports",
    ],
}


@receiver(post_save, sender=DiagnosticCenter)
def create_default_roles(
    sender: type[DiagnosticCenter],
    instance: DiagnosticCenter,
    created: bool,
    **kwargs,
) -> None:
    """Create default roles with permissions for a newly created center."""
    if not created:
        return

    all_perms = list(Permission.objects.all())
    perm_map = {p.codename: p for p in all_perms}

    for role_name, perm_codenames in DEFAULT_ROLE_PERMS.items():
        role, _ = Role.objects.get_or_create(
            name=role_name,
            center=instance,
            defaults={"is_system": True},
        )
        if perm_codenames is None:
            role.permissions.set(all_perms)
        else:
            role.permissions.set([perm_map[c] for c in perm_codenames if c in perm_map])
    # Grant all permissions as available for this center
    instance.available_permissions.set(all_perms)

    logger.info(
        "Created default roles for center %s (id=%s)",
        instance.name,
        instance.id,
    )
