---
name: celery-inspect
description: Inspect Celery workers, queues, and task status for the ADPP backend. Use when debugging task failures, checking queue backlogs, monitoring worker health, or investigating why a task isn't running.
---

# Celery Queue & Worker Inspector

Inspect the state of Celery workers, queues, and tasks in the ADPP backend.

## Arguments

`$ARGUMENTS` — optional: `workers`, `queues`, `active`, `reserved`, `failed`, or a task ID.

## Instructions

### Inspect Workers
```bash
cd /Users/mdshampadsharkar/Desktop/adpp/adpp-backend
ENV_PATH=./adpp_backend/env/dev.env.yaml poetry run celery -A config.celery.app inspect active
```

### Inspect Queues
```bash
ENV_PATH=./adpp_backend/env/dev.env.yaml poetry run celery -A config.celery.app inspect active_queues
```

### Check Scheduled Tasks (Celery Beat)
```bash
ENV_PATH=./adpp_backend/env/dev.env.yaml poetry run celery -A config.celery.app inspect scheduled
```

### Check Reserved Tasks
```bash
ENV_PATH=./adpp_backend/env/dev.env.yaml poetry run celery -A config.celery.app inspect reserved
```

### Check Task Result
```bash
ENV_PATH=./adpp_backend/env/dev.env.yaml poetry run python -c "
from config.celery import app
result = app.AsyncResult('$ARGUMENTS')
print(f'State: {result.state}')
print(f'Result: {result.result}')
print(f'Traceback: {result.traceback}')
"
```

### ADPP Queue Configuration

The ADPP backend uses these Celery queues:
- `default` — General tasks, MI validity checks
- `cronjobs` — Scheduled tasks (report generation, index reports)
- `importer` — Service importer data downloads
- `payment` — Revenue calculation and payment processing
- `amp` — AMP page generation
- `notification` — Email/Slack notifications

### Flower Dashboard

If Flower is running, it's accessible at the configured Flower port. Check Kubernetes deployment for the URL.

## Output Format

Present results in a structured table:
```
Queue: <name>
Active Workers: <count>
Active Tasks: <count>
Reserved: <count>
```

For failed tasks, show:
- Task name and ID
- Exception type and message
- Timestamp
- Retry count
