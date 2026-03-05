---
globs: "**/tasks.py"
---

# Celery Task Conventions

## Task Types

### @shared_task — Simple async tasks
```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=360,
    retry_kwargs={'max_retries': 3},
    queue='default',
)
def my_task(self, **kwargs):
    logger.info('Starting my_task')
    ...
```

### SingleTask — Tasks with distributed locks
```python
from config.celery import app
from src.tasks import SingleTask

class MyTask(SingleTask):
    lock_timeout = 60 * 60  # seconds
    queue = 'default'
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 360
    retry_kwargs = {'max_retries': 3}

    def run(self):
        ...

my_task = app.register_task(MyTask)
```

## Required Settings

- `retry_backoff=True` — exponential backoff on retries
- `retry_backoff_max=360` — max 6 minutes between retries
- `retry_kwargs={'max_retries': 3}` — limit retry attempts
- `queue='<queue_name>'` — always specify the queue

## Queue Assignment

| Queue | Use for |
|-------|---------|
| `default` | General tasks |
| `cronjobs` | Scheduled periodic tasks |
| `importer` | Data import operations |
| `payment` | Revenue/payment processing |
| `amp` | AMP page generation |
| `notification` | Email/Slack alerts |

## Production Guards

```python
from config.settings import DeployEnv

if settings.DEPLOY_ENV != DeployEnv.Production:
    return
```

## Logging

Always use `from src.utils.logger import get_logger; logger = get_logger(__name__)`.
