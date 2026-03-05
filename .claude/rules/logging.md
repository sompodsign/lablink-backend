---
globs: "**/*.py"
---

# Logging Rules

## Setup

Always use the project's structured logger:
```python
from src.utils.logger import get_logger

logger = get_logger(__name__)
```

NEVER use `print()`, `logging.getLogger()`, or `logging.basicConfig()`.

## Usage

Use structured key-value logging:
```python
logger.info('Import completed', service_importer_id=si.id, rows=count)
logger.error('Import failed', service_importer_id=si.id, exc_info=True)
logger.warning('Rate limited', url=url, status=res.status_code)
```

Always pass `exc_info=True` when logging exceptions to capture the traceback.

## NEVER Log

- Credentials, passwords, API keys, or tokens
- `_account_info` values (encrypted field content)
- Full HTTP response bodies from external APIs (truncate to first 500 chars if needed)
- User PII beyond what's needed for debugging
