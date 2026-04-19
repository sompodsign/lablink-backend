"""
Django settings for production environment.
"""

from .base import *  # noqa: F401, F403

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}


# Celery Configuration
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")

# Celery Beat Schedule — daily subscription/billing tasks
CELERY_BEAT_SCHEDULE = {
    "check-trial-expirations": {
        "task": "subscriptions.check_trial_expirations",
        "schedule": 86400,  # every 24 hours
    },
    "send-trial-expiry-warning": {
        "task": "subscriptions.send_trial_expiry_warning",
        "schedule": 86400,
    },
    "generate-monthly-invoices": {
        "task": "subscriptions.generate_monthly_invoices",
        "schedule": 86400,
    },
    "mark-overdue-invoices": {
        "task": "subscriptions.mark_overdue_invoices",
        "schedule": 86400,
    },
    "expire-inactive-subscriptions": {
        "task": "subscriptions.expire_inactive_subscriptions",
        "schedule": 86400,
    },
}

# CORS Configuration - Strict in production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOWED_ORIGIN_REGEXES = [
    env("CORS_ALLOWED_ORIGIN_REGEX", default=r"^https?://[\w-]+\.lablink\.bd$"),
]
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Security settings for production
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
# TODO: Enable HSTS after setting up SSL (Let's Encrypt)
# SECURE_HSTS_SECONDS = 31536000  # 1 year
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# ── Email via Amazon SES SMTP ──────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="email-smtp.ap-southeast-1.amazonaws.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="LabLink <noreply@lablink.bd>")

# ── Frontend URL (for notification links) ────────────────────────
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

# ── Google Cloud Storage — Static Files ──────────────────────────
GCS_BUCKET_NAME = env("GCS_BUCKET_NAME", default="")
GCS_CREDENTIALS_FILE = env(
    "GCS_CREDENTIALS_FILE", default="/run/secrets/gcs-credentials.json"
)

# Always serve static from GCS when bucket is configured
if GCS_BUCKET_NAME:
    STATIC_URL = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/static/"

# Only activate GCS upload backend if credentials file exists (CI only)
import os as _os  # noqa: E402

if GCS_BUCKET_NAME and _os.path.exists(GCS_CREDENTIALS_FILE):
    from google.oauth2.service_account import Credentials as _GCSCreds  # noqa: E402

    _gcs_credentials = _GCSCreds.from_service_account_file(GCS_CREDENTIALS_FILE)

    INSTALLED_APPS += ["storages"]  # type: ignore[name-defined]  # noqa: F405

    STORAGES = {
        "staticfiles": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": GCS_BUCKET_NAME,
                "credentials": _gcs_credentials,
                "location": "static",
                "querystring_auth": False,
            },
        },
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
    }
