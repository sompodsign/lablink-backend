"""
Django base settings for LabLink project.

This file contains settings shared across all environments.
Environment-specific settings should go in local.py, stg.py, or prod.py.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Load .env file
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, "env", ".env"))


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "django_celery_results",
    "django_celery_beat",
    # Local apps
    "core.users",
    "core.tenants",
    "apps.appointments",
    "apps.diagnostics",
    "apps.payments",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.tenants.middleware.TenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Custom User Model
AUTH_USER_MODEL = "users.User"

# REST Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/minute",
        "user": "300/minute",
        "public_booking": "20/hour",
    },
}

# Authentication backends — allow login with email or username
AUTHENTICATION_BACKENDS = [
    "core.users.backends.EmailOrUsernameBackend",
]

# JWT Configuration
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=90),  # 3 months
    "REFRESH_TOKEN_LIFETIME": timedelta(days=180),  # 6 months
}

# Email Configuration (console backend for development)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@lablink.com.bd"

# drf-spectacular Configuration
SPECTACULAR_SETTINGS = {
    "TITLE": "LabLink API",
    "DESCRIPTION": (
        "## Multi-Tenant Diagnostic Center Management API\n\n"
        "LabLink provides APIs for managing diagnostic centers, patients, appointments, "
        "test orders, reports, and payments — all scoped to a specific diagnostic center "
        "(tenant) determined by the request subdomain.\n\n"
        "### Authentication\n\n"
        "All endpoints (except tenant info and registration) require **JWT Bearer** authentication.\n\n"
        "1. **Obtain token**: `POST /api/token/` with `username` + `password`\n"
        "2. **Use token**: Add header `Authorization: Bearer <access_token>`\n"
        "3. **Refresh token**: `POST /api/token/refresh/` with `refresh` token\n\n"
        "### Multi-Tenancy\n\n"
        "Every request is scoped to a diagnostic center based on the subdomain:\n"
        '- `popularhospital.lablink.com.bd` → data for "Popular Hospital"\n'
        "- `demo.localhost:8200` → demo center (local dev)\n\n"
        "All list/retrieve queries are automatically filtered to the current center. "
        "Cross-tenant data access is impossible by design.\n\n"
        "### Roles\n\n"
        "| Role | Description |\n"
        "|------|-------------|\n"
        "| **Admin** | Center administrator — full access |\n"
        "| **Receptionist** | Front desk staff — patient registration, appointments |\n"
        "| **Lab Technician** | Lab staff — test orders, report creation |\n"
        "| **Doctor** | Consultations, test prescriptions |\n"
        "| **Patient** | View own appointments and reports |\n"
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/",
    "TAGS": [
        {
            "name": "Authentication",
            "description": "JWT token management and user registration",
        },
        {"name": "Tenant", "description": "Diagnostic center info (public)"},
        {
            "name": "Patients",
            "description": "Patient registration and management (staff/doctor)",
        },
        {
            "name": "Doctors",
            "description": "Doctor management and activity (staff/admin)",
        },
        {"name": "Staff", "description": "Staff listing (admin)"},
        {
            "name": "Appointments",
            "description": "Appointment scheduling and consultation",
        },
        {
            "name": "Test Orders",
            "description": "Lab test prescriptions and queue management",
        },
        {
            "name": "Reports",
            "description": "Lab report creation, verification, and delivery",
        },
        {"name": "Payments", "description": "Payment recording and tracking"},
        {
            "name": "Diagnostics",
            "description": "Test types and center-specific pricing",
        },
    ],
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "filter": True,
    },
    "ENUM_NAME_OVERRIDES": {
        "BloodGroupEnum": "core.users.models.PatientProfile.BloodGroup",
        "TestOrderStatusEnum": "apps.diagnostics.models.TestOrder.Status",
        "TestOrderPriorityEnum": "apps.diagnostics.models.TestOrder.Priority",
        "ReportStatusEnum": "apps.diagnostics.models.Report.Status",
        "PaymentMethodEnum": "apps.payments.models.Payment.Method",
        "PaymentStatusEnum": "apps.payments.models.Payment.Status",
        "AppointmentStatusEnum": [
            ("PENDING", "Pending"),
            ("CONFIRMED", "Confirmed"),
            ("COMPLETED", "Completed"),
            ("CANCELLED", "Cancelled"),
        ],
    },
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],
    # Coerce all untyped path params (id) to integer
    "SCHEMA_COERCE_PATH_PK_SUFFIX": True,
}
