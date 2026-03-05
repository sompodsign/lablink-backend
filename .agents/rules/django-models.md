---
trigger: glob
glob: "**/models.py"
---

# Django Model Conventions

## Base Class

Always inherit from `BaseModel` (from `src.models`):
```python
from src.models import BaseModel

class MyModel(BaseModel):
    ...
```

`BaseModel` provides: `create_date`, `update_date`, `BaseManager`, `pre_update()`, `pre_update_check()`.

## Meta Class

```python
class Meta:
    db_table = 'prefix_model_name'  # REQUIRED — use core_, apps_, ats_, ads_, admob_, pwa_, amp_
    verbose_name = _('model name')  # Use gettext_lazy
    verbose_name_plural = _('model names')
```

## Field Conventions

- ForeignKey: always set explicit `on_delete` — prefer `models.PROTECT`, use `CASCADE` only when appropriate
- Choices: use `models.TextChoices` or `models.IntegerChoices` as inner class:
  ```python
  class Status(models.IntegerChoices):
      ACTIVE = 1, _('Active')
      INACTIVE = 2, _('Inactive')
  ```
- Indexes: use `PgIndex` (from `src.models`) for PostgreSQL-specific indexes
- Encrypted fields: use `CredentialsField` (from `src.fields`) for sensitive data

## Historical Records

When audit trail is needed:
```python
from simple_history.models import HistoricalRecords

history = HistoricalRecords(
    table_name='prefix_model_name_historical',
    excluded_fields=['field_to_exclude'],
)
```

## IMPORTANT

- NEVER use `filter().update()` on `CredentialsField` from local dev — it encrypts with the local SECRET_KEY
- Use `pre_update()` pattern for model updates (returns changed fields list)
- Use `gettext_lazy` (imported as `_`) for all user-facing strings
