---
name: openapi-docs
description: Enforce drf-spectacular OpenAPI documentation on every DRF ViewSet and APIView. Use whenever creating or modifying Django REST Framework views, serializers, or URL routes.
---

# OpenAPI Documentation Standard (drf-spectacular)

Every Django REST Framework view **MUST** have complete OpenAPI documentation using `drf-spectacular`. This is not optional — undocumented endpoints are unacceptable.

## When This Skill Applies

- Creating a new ViewSet, APIView, or `@action`
- Modifying an existing view's request/response contract
- Adding or changing serializers used by views
- Adding new URL routes

## Required Imports

```python
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
)
```

## Rules

### 1. Every ViewSet MUST use `@extend_schema_view`

Decorate the class with `@extend_schema_view` mapping **every** action to an `extend_schema()` call:

```python
@extend_schema_view(
    list=extend_schema(
        tags=['Patients'],
        summary='List patients',
        description='Returns patients registered at the current center.',
    ),
    retrieve=extend_schema(
        tags=['Patients'],
        summary='Get patient detail',
        description='Retrieve a single patient profile with medical history.',
    ),
    create=extend_schema(
        tags=['Patients'],
        summary='Register a walk-in patient',
        description=(
            'Staff registers a new patient at the current center. '
            'Creates a User without login credentials and a PatientProfile.'
        ),
        request=PatientRegistrationSerializer,
        responses={201: PatientSerializer},
        examples=[
            OpenApiExample(
                'Register walk-in patient',
                value={
                    'first_name': 'Fatima',
                    'last_name': 'Khan',
                    'phone_number': '01700000099',
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=['Patients'],
        summary='Update patient info',
        description='Staff updates patient profile.',
    ),
)
class PatientViewSet(viewsets.ModelViewSet):
    ...
```

### 2. Every custom `@action` MUST have its own `@extend_schema`

Place `@extend_schema` directly above the `@action` decorator:

```python
@extend_schema(
    tags=['Reports'],
    summary='Verify a report',
    description=(
        'Staff verifies a draft report, changing status to VERIFIED. '
        'The verifying user is recorded. Can only be verified once.'
    ),
    request=None,
    responses={200: ReportSerializer},
)
@action(detail=True, methods=['post'], url_path='verify')
def verify(self, request, pk=None):
    ...
```

### 3. Every standalone APIView MUST have `@extend_schema`

```python
@extend_schema(
    tags=['Tenant'],
    summary='Get current center info',
    description='Returns branding and configuration. No authentication required.',
    responses={200: DiagnosticCenterSerializer},
)
class CurrentTenantView(APIView):
    ...
```

### 4. Required `@extend_schema` Parameters

Every `extend_schema()` call **MUST** include:

| Parameter     | Required                                    | When                                                          |
| ------------- | ------------------------------------------- | ------------------------------------------------------------- |
| `tags`        | **Always**                                  | Group by domain (e.g., `['Patients']`, `['Test Orders']`)     |
| `summary`     | **Always**                                  | Short one-line description (sentence case, no period)         |
| `description` | **Always for create/update/custom actions** | Multi-line explanation of behavior, permissions, side effects |
| `request`     | When serializer differs from default        | Explicit request serializer class                             |
| `responses`   | When response differs from default          | e.g., `{201: PatientSerializer}` for create                   |
| `examples`    | **Always for create/update**                | At least one realistic `OpenApiExample`                       |
| `parameters`  | When using query params                     | `OpenApiParameter` for filters, search, etc.                  |

### 5. Example Payloads Must Be Realistic

Use **domain-appropriate** data, not generic placeholders:

```python
# GOOD — realistic, domain-specific
OpenApiExample(
    'Order a CBC test (urgent)',
    value={
        'appointment': 1,
        'test_type': 3,
        'priority': 'URGENT',
        'clinical_notes': 'Patient reports persistent fatigue and dizziness.',
    },
    request_only=True,
)

# BAD — generic, unhelpful
OpenApiExample(
    'Example',
    value={'field1': 'value1', 'field2': 'value2'},
    request_only=True,
)
```

### 6. Multiple Examples for Create Endpoints

Provide at least 2 examples for `create` actions when there are optional fields or different use patterns:

```python
examples=[
    OpenApiExample(
        'Full registration',
        value={'first_name': 'Fatima', 'last_name': 'Khan', 'phone_number': '017...', 'blood_group': 'B+'},
        request_only=True,
    ),
    OpenApiExample(
        'Minimal registration',
        value={'first_name': 'Rahim', 'last_name': 'Uddin'},
        request_only=True,
    ),
]
```

### 7. Query Parameter Documentation

When a view supports query parameter filtering, document them explicitly:

```python
@extend_schema(
    parameters=[
        OpenApiParameter(
            name='status',
            description='Filter by test order status',
            required=False,
            type=str,
            enum=['PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'],
        ),
    ],
)
```

### 8. Tags Must Match `SPECTACULAR_SETTINGS['TAGS']`

Use only tags defined in `core/config/base.py` → `SPECTACULAR_SETTINGS['TAGS']`:

| Tag              | Use for                          |
| ---------------- | -------------------------------- |
| `Authentication` | Login, register, token endpoints |
| `Tenant`         | Public center info               |
| `Patients`       | Patient CRUD                     |
| `Doctors`        | Doctor management                |
| `Staff`          | Staff listing                    |
| `Appointments`   | Scheduling, consultation         |
| `Test Orders`    | Lab test prescriptions           |
| `Reports`        | Report CRUD, verification        |
| `Payments`       | Payment recording                |
| `Diagnostics`    | Test types, pricing              |

If a new domain is needed, **add the tag** to `SPECTACULAR_SETTINGS['TAGS']` first.

### 9. Descriptions Must Explain Special Behavior

Always document in the `description`:

- **Who can access** (role requirements)
- **Tenant scoping** (if data is filtered by center)
- **Side effects** (e.g., "Test order status is automatically set to COMPLETED")
- **Validation rules** (e.g., "Test type must be available at this center")
- **Auto-populated fields** (e.g., "Center and ordering doctor are set automatically")

### 10. Enum Registration

When adding a new `TextChoices` field, register it in `SPECTACULAR_SETTINGS['ENUM_NAME_OVERRIDES']`:

```python
# In core/config/base.py
SPECTACULAR_SETTINGS = {
    'ENUM_NAME_OVERRIDES': {
        'MyNewStatusEnum': 'apps.myapp.models.MyModel.Status',
    },
}
```

## Validation

After making changes, always run:

```bash
DJANGO_SETTINGS_MODULE=core.config.local .venv/bin/python manage.py spectacular --validate
```

The schema must generate with **0 errors**. Warnings about path parameter types are acceptable (tenant-scoped ViewSets).

## Anti-Patterns to Avoid

- ❌ ViewSet with no `@extend_schema_view` — endpoints show up as "No description"
- ❌ `@action` without `@extend_schema` — custom actions are invisible in docs
- ❌ Generic examples like `{'key': 'value'}` — unhelpful to API consumers
- ❌ Missing `tags` — endpoints end up in an "Other" group
- ❌ Using `drf-yasg` decorators (`@swagger_auto_schema`) — project uses `drf-spectacular`
- ❌ Hardcoded response dicts in `responses` — use serializer classes
- ❌ Forgetting `request_only=True` on request examples — they leak into response docs
