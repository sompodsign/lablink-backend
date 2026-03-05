"""
Django settings for local development.
"""

from .base import *  # noqa: F401, F403

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-760!s-95ydau2+w7x8&wy)cnvs#)r!09l@88p*7!h)k2+(ayba')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB', default='lablink'),
        'USER': env('POSTGRES_USER', default='lablink_user'),
        'PASSWORD': env('POSTGRES_PASSWORD', default='lablink_password'),
        'HOST': env('POSTGRES_HOST', default='localhost'),
        'PORT': env('POSTGRES_PORT', default='5432'),
    }
}


# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

# CORS Configuration - Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://localhost:5173',
    'http://*.lvh.me',      # For local subdomain testing (e.g., http://tenant1.lvh.me:8000)
    'http://*.localhost',   # For local subdomain testing
]
