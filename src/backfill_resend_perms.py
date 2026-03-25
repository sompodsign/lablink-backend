import logging

from django.db import transaction

from core.tenants.models import Permission, Role

logger = logging.getLogger(__name__)

# The two new permissions
perms = Permission.objects.filter(codename__in=["resend_email", "resend_sms"])

if not perms:
    logger.info("Permissions not found!")
else:
    with transaction.atomic():
        roles = Role.objects.filter(
            name__in=["Admin", "Receptionist", "Medical Technologist"]
        )
        count = 0
        for role in roles:
            # Only add if the center actually has the permission available
            if role.center.available_permissions.filter(
                codename="resend_email"
            ).exists():
                role.permissions.add(*perms)
                count += 1
        logger.info(f"Granted resend_email and resend_sms to {count} existing roles.")
