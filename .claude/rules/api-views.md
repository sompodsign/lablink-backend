---
globs: "{**/views.py,**/serializers.py}"
---

# REST API Conventions

## Serializers

Inherit from project's `ModelSerializer` (from `src/serializers.py`), NOT from `rest_framework.serializers.ModelSerializer` directly:

```python
from src.serializers import ModelSerializer

class MySerializer(ModelSerializer):
    class Meta:
        model = MyModel
        fields = (...)
        read_only_fields = (...)
```

Use `self.request_user` and `self.request_account` properties (provided by `BaseSerializer`).

For nested creates/updates, use `NestedModelSerializer` from `src/serializers.py`.

## ViewSets

- Always scope queries to the user: `queryset.filter_by_user(self.request.user)`
- Optimize queries — use `only()`, `select_related()`, `prefetch_related()`:
  ```python
  def get_queryset(self):
      return self.queryset.select_related('owner').filter_by_user(self.request.user)
  ```
- Use `get_only_fields(instance=self)` for field-level optimization

## Error Response Format

All API errors must follow:
```python
{'status_code': int, 'errors': str | list | dict}
```

Use `views.set_rollback()` inside `@transaction.atomic` when returning error responses.

## N+1 Query Prevention

- NEVER access ForeignKey fields in loops without `select_related()`
- NEVER access reverse relations in loops without `prefetch_related()`
- Use `only()` when you need a subset of fields
