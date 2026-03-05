---
globs: "**/types.py"
---

# Pydantic Model Rules (API Response Types)

## General

- Use Pydantic v2 `BaseModel` for all API response data models
- Use `Decimal` for revenue/money fields — NEVER `float`
- Use `schema` library (NOT Pydantic) for `ACCOUNT_INFO_SCHEMA` in `schema.py`

## Field Validators

Coerce fields that may arrive as int/None from APIs:
```python
@field_validator('app_id', mode='before')
@classmethod
def coerce_to_str(cls, v: Any) -> str:
    return str(v) if v is not None else ''
```

## Anti-Patterns to Avoid

- DON'T add `Field(alias='x')` when alias matches the field name — Pydantic v2 uses field name by default
- DON'T add `default=0` or `default=''` on fields that MUST be present in the API response — these mask parse failures; required fields should be required
- DON'T silently handle None in validators for required fields — let Pydantic raise `ValidationError`
- DON'T add validators for fields that already return the correct type from the API — remove redundant coercion

## Response Wrapper

```python
class SomeReportResponse(BaseModel):
    results: list[SomeReportRow] = Field(default_factory=list)
```

Use `Field(default_factory=list)` for list fields so empty responses parse correctly.
