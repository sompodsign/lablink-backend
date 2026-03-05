---
trigger: glob
glob: "**/*.py"
---

# Logging Rules

## Setup

Always use Python's standard logging:
```python
import logging

logger = logging.getLogger(__name__)
```

NEVER use `print()` or `logging.basicConfig()` in application code.

## Usage

Use structured key-value logging:
```python
logger.info('Translation completed', extra={'user_id': user.id, 'word': word})
logger.error('AI request failed', extra={'prompt': prompt[:100]}, exc_info=True)
logger.warning('Rate limited', extra={'url': url, 'status': res.status_code})
```

Always pass `exc_info=True` when logging exceptions to capture the traceback.

## NEVER Log

- Credentials, passwords, API keys, or tokens
- Full HTTP response bodies from external APIs (truncate to first 500 chars if needed)
- User PII beyond what's needed for debugging
