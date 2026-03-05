---
trigger: glob
glob: "**/*.py"
---

# Error Handling Rules

## General

- Always catch specific exceptions — never bare `except:` or `except Exception:`
- Use `transaction.set_rollback(True)` before returning errors inside `@transaction.atomic`
- Never expose raw Python tracebacks to API clients

## HTTP Response Parsing

Always catch both JSON and validation errors together:
```python
try:
    data = response.json()
    parsed = MyModel.model_validate(data)
except (json.JSONDecodeError, ValidationError) as exc:
    raise ValueError(f'Failed to parse: {exc}') from exc
```

## Logging Severity

- `logger.warning(exc, exc_info=True)` — for 4xx client errors, expected failures
- `logger.error(exc, exc_info=True)` — for 5xx server errors, unexpected failures
- `logger.info(...)` — for operational events (task started, completed)

## DRF API Views

```python
from rest_framework import status
from rest_framework.response import Response

try:
    ...
except ValidationError as e:
    return Response(
        {'status_code': 400, 'errors': str(e)},
        status=status.HTTP_400_BAD_REQUEST
    )
```
