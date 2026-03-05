---
globs: "**/*.py"
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
    raise ImporterParseException(f'Failed to parse: {exc}') from exc
```

## Logging Severity

- `logger.warning(exc, exc_info=True)` — for 4xx client errors, expected failures
- `logger.error(exc, exc_info=True)` — for 5xx server errors, unexpected failures
- `logger.info(...)` — for operational events (task started, completed)

## Importer-Specific

- Use `ImporterParseException` for all parse/data errors in importers
- Use `self._raise_for_status(res)` after every HTTP response (from `APIMixin`)
- Wrap entire `_request_report_data()` logic in proper exception handling

## GraphQL Mutations

```python
except ValidationError as e:
    transaction.set_rollback(True)
    return MutationResponse(success=False, errors=to_gql_validation_errors(e))
except Exception as e:
    transaction.set_rollback(True)
    return MutationResponse(success=False, errors=[NonFieldErrorType(messages=[str(e)])])
```
