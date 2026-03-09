---
trigger: always_on
---

# Testing Conventions

## Mandatory Unit Tests

- **Always write unit tests** for any new or modified code — no exceptions.
- Tests must accompany every feature, bug fix, refactor, or API change.
- Place tests in the app's `tests/` directory or `tests.py` file.
- If a test file doesn't exist yet, create one.

## Test Classes

- `django.test.TestCase` — for tests that need database access
- `django.test.SimpleTestCase` — for pure logic tests (no DB)
- `rest_framework.test.APITestCase` — for authenticated API endpoint tests

## Running Tests

```bash
cd src && python manage.py test <test_path> --keepdb -v 3
```

## Mocking

- Patch where the object is IMPORTED, not where it's DEFINED:
  ```python
  # CORRECT — patch in the module that imports it
  @patch('src.apps.api.views.AIClient')

  # WRONG — patching at the definition site
  @patch('src.ai.client.AIClient')
  ```

## Assertions

- Use specific assertion methods: `assertIs`, `assertIsNone`, `assertIn`, `assertRaises`
- Use `assertEqual` with `Decimal` for money comparisons, never float
