---
name: task-scaffold
description: Scaffold a new Celery task for the ADPP backend. Use when creating new async tasks, scheduled jobs, or background workers. Generates task code following ADPP conventions including retry policies, logging, and queue assignment.
---

# Scaffold Celery Task

Generate a new Celery task following ADPP backend conventions.

## Arguments

`$ARGUMENTS` should contain: `<app_name>` `<task_name>` and optionally the task type (`shared_task` or `SingleTask`).

## Instructions

### Step 1: Determine Task Type

ADPP uses two task patterns:

#### Pattern 1: `@shared_task` — Simple async tasks
Best for: one-off operations, API calls, data processing

```python
from celery import shared_task
from src.utils.logger import get_logger

logger = get_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=360,
    retry_kwargs={'max_retries': 3},
    queue='default',
)
def <task_name>(self, **kwargs):
    """<Task description>."""
    logger.info(f'Starting <task_name>')
    # Task implementation
    logger.info(f'Completed <task_name>')
```

#### Pattern 2: `SingleTask` — Complex tasks with locking
Best for: scheduled jobs that should only run one instance at a time

```python
from config.celery import app
from src.tasks import SingleTask
from src.utils.logger import get_logger

logger = get_logger(__name__)


class <TaskName>Task(SingleTask):
    lock_timeout = 60 * 60  # Lock duration in seconds
    queue = 'default'
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 360
    retry_kwargs = {'max_retries': 3}

    def run(self):
        """<Task description>."""
        logger.info(f'Starting {self.__class__.__name__}')
        # Task implementation
        logger.info(f'Completed {self.__class__.__name__}')


<task_name> = app.register_task(<TaskName>Task)
```

### Step 2: Choose the Right Queue

| Queue | Use for |
|-------|---------|
| `default` | General-purpose tasks |
| `cronjobs` | Scheduled periodic tasks |
| `importer` | Data import operations |
| `payment` | Revenue/payment calculations |
| `amp` | AMP page generation |
| `notification` | Email/Slack notifications |

### Step 3: Add to tasks.py

Place the task in:
```
adpp_backend/src/apps/<app_name>/tasks.py
```

Or if the app doesn't have a `tasks.py`, create one with proper imports.

### Step 4: Register with Celery Beat (if periodic)

If the task should run on a schedule, add it to the Celery Beat configuration in:
```
adpp_backend/config/celery.py
```

```python
app.conf.beat_schedule['<task_name>'] = {
    'task': 'src.apps.<app_name>.tasks.<task_name>',
    'schedule': crontab(hour=0, minute=0),  # Adjust schedule
    'options': {'queue': '<queue_name>'},
}
```

## Important Conventions

- Always use `get_logger(__name__)` for logging
- Always set `retry_backoff=True` with `retry_backoff_max=360`
- Set appropriate `lock_timeout` for SingleTask (prevents concurrent execution)
- Use `queue` parameter to route to the correct worker
- Production checks: use `if settings.DEPLOY_ENV != DeployEnv.Production: return` for prod-only tasks
- Import `DeployEnv` from `config.settings` for environment checks
