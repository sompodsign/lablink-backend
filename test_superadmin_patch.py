import requests
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from core.tenants.models import DiagnosticCenter
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()
c = DiagnosticCenter.objects.first()

client = APIClient()
client.force_authenticate(user=admin)
res = client.patch(f'/api/tenants/superadmin/centers/{c.id}/', {'can_use_sms': 'true', 'can_use_email': 'true', 'can_use_ai': 'true'}, format='multipart')
print('Status:', res.status_code)
c.refresh_from_db()
print('DB states:', c.can_use_sms, c.can_use_email, c.can_use_ai)
