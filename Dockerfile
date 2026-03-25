
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    DJANGO_SETTINGS_MODULE=core.config.prod

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock* /app/

# Install dependencies (no virtualenv inside container)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy project
COPY . /app/

# Entrypoint: run migrations, collect static, then start Gunicorn
COPY <<'EOF' /app/entrypoint.sh
#!/bin/sh
set -e

# Write GCS service-account credentials from env var (injected at runtime)
if [ -n "$GCS_CREDENTIALS_JSON" ]; then
    mkdir -p /run/secrets
    printf '%s' "$GCS_CREDENTIALS_JSON" > /run/secrets/gcs-credentials.json
fi

echo " Starting Gunicorn..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
EOF

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
CMD ["/app/entrypoint.sh"]
