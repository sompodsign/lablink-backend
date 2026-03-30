import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.config.local')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
django.setup()

from core.tenants.models import DiagnosticCenter
from core.tenants.superadmin_serializers import SuperadminCenterDetailSerializer

count = DiagnosticCenter.objects.count()
print(f"Total Centers: {count}")

center = DiagnosticCenter.objects.first()
if center:
    serializer = SuperadminCenterDetailSerializer(center, context={'request': None})
    print("\n--- API OUTPUT FOR DIAGNOSTIC CENTER ---")
    print(json.dumps(serializer.data, indent=2))
else:
    print("Database is empty, no centers found.")
