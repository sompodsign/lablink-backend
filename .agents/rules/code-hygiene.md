---
trigger: glob
glob: "**/*.py"
---

# Code Hygiene — No Dead Weight

## Unnecessary Parameters

- If a subclass `__init__` only calls `super().__init__(*args, **kwargs)` with no extra logic, **delete the entire `__init__`** — Python uses the parent's automatically
- Don't accept `**kwargs` in method overrides if you never read from it — match the parent's concrete signature
- Before adding a parameter, check: is this value already on `self`? If so, don't pass it

```python
# BAD — __init__ does nothing but forward
class MyView(BaseView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# GOOD — omit entirely
class MyView(BaseView):
    pass
```

## Unnecessary Fallbacks

- Don't use `value or default` when the system guarantees `value` is present
- Don't use `kwargs.get('key', default) or default` — the `or default` is redundant
- Don't write `return data or None` — be explicit

## Dead Conditions

- Before writing an `if` check, trace where the variable comes from — if already validated/guaranteed upstream, the condition is dead
- Don't add `if value is not None` after Pydantic validation on a required (non-Optional) field
- Don't add type-coercion validators for fields the API already returns in the correct type

## Chain Audit

When touching a method chain (caller → method → sub-method), audit the full chain:
1. Is every parameter **read** (not just forwarded)? Remove unread ones.
2. Is every fallback **reachable**? If the value is guaranteed, remove the fallback.
3. Is every condition's **false branch reachable**? If not, remove the condition.
