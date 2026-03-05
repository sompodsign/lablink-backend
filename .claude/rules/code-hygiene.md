---
globs: "**/*.py"
---

# Code Hygiene — No Dead Weight

## Unnecessary Parameters

- If a subclass `__init__` only calls `super().__init__(*args, **kwargs)` with no extra logic, **delete the entire `__init__`** — Python uses the parent's automatically
- Don't accept `**kwargs` in method overrides if you never read from it — match the parent's concrete signature
- Before adding a parameter, check: is this value already on `self`? If so, don't pass it

```python
# BAD — __init__ does nothing but forward
class MyImporter(BaseImporter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# GOOD — omit entirely
class MyImporter(BaseImporter):
    pass

# BAD — **kwargs accepted but unused
def _get_source(self, account=None, **kwargs):
    return App.objects.filter(account=account)

# GOOD — only declare what you use
def _get_source(self, account=None):
    return App.objects.filter(account=account)
```

## Unnecessary Fallbacks

- Don't use `value or default` when the system guarantees `value` is present (required Pydantic field, non-nullable DB column, already-validated input)
- Don't use `kwargs.get('key', default) or default` — the `or default` is redundant
- Don't write `return data or None` — be explicit: `return data if data else None` or just `return data`

```python
# BAD — double default
extra_filters = kwargs.get('extra_filters', {}) or {}

# GOOD
extra_filters = kwargs.get('extra_filters', {})

# BAD — revenue is a required Pydantic field, guaranteed present
revenue = row.revenue or Decimal(0)

# GOOD — trust the validated model
revenue = row.revenue
```

## Dead Conditions

- Before writing an `if` check, trace where the variable comes from — if already validated/guaranteed upstream, the condition is dead
- Don't add `if value is not None` after Pydantic validation on a required (non-Optional) field
- Don't add type-coercion `@field_validator` for fields the API already returns in the correct type
- Don't add `isinstance()` checks after Pydantic/serializer validation has already enforced the type

```python
# BAD — revenue is required in Pydantic model, can never be None
if row.revenue is not None:
    total += row.revenue

# GOOD — trust validated data
total += row.revenue

# BAD — API returns app_id as str, validator is redundant
@field_validator('app_id', mode='before')
def coerce_to_str(cls, v):
    return str(v) if v is not None else ''

# GOOD — remove validator, declare the type
app_id: str
```

## Chain Audit

When touching a method chain (caller → method → sub-method), audit the full chain:
1. Is every parameter **read** (not just forwarded)? Remove unread ones.
2. Is every fallback **reachable**? If the value is guaranteed, remove the fallback.
3. Is every condition's **false branch reachable**? If not, remove the condition.
