---
globs: "{**/tests/**,**/tests.py}"
---

# Testing Conventions

## Test Classes

- `django.test.TestCase` — for tests that need database access
- `django.test.SimpleTestCase` — for pure logic tests (no DB)
- `AdminUserAPITestCase` — for authenticated API endpoint tests
- `ServiceImporterAPITestCase` — for importer-specific API tests

## Factories

Use Factory Boy factories from each app's `factories.py`:
```python
from src.apps.importer.factories import ServiceImporterFactory

self.service_importer = ServiceImporterFactory(account_info=ACCOUNT_INFO)
```

NEVER create model instances manually in tests when a factory exists.

## Importer Tests

- Tag with `@tag('importer')` — these are excluded from default test runs
- `ACCOUNT_INFO` dict keys MUST match the credential fields in `schema.py`
- Use `@test_importer_download` decorator for download tests
- Mock external HTTP calls — never make real API requests in tests

## Mocking

- Patch where the object is IMPORTED, not where it's DEFINED:
  ```python
  # CORRECT — patch in the module that imports it
  @patch('src.apps.importer.modules.service.importers.five.main.get_retry_session')

  # WRONG — patching at the definition site
  @patch('src.utils.get_retry_session')
  ```

## Assertions

- Use `Decimal` for revenue comparisons, never float:
  ```python
  self.assertEqual(row.revenue, Decimal('500'))
  ```
- Use specific assertion methods: `assertIs`, `assertIsNone`, `assertIn`, `assertRaises`

## Running Tests

```bash
ENV_PATH=./adpp_backend/env/test.env-unit-test.yaml poetry run coverage run ./adpp_backend/manage.py test -d ./adpp_backend/<path> --keepdb -v 3
```

Min coverage requirement: 64%.
