---
description: Run task-related unit tests for code modified during the current task
---

# Run Tests

1. Identify changed files from the current task/branch
2. Find corresponding test files
3. Run the relevant tests

```bash
cd src && python manage.py test <test_path> --keepdb -v 3
```

### Examples
```bash
cd src && python manage.py test apps.lessons --keepdb -v 3
cd src && python manage.py test apps.api.tests.test_views.DictionarySearchTestCase --keepdb -v 3
cd src && python manage.py test --keepdb -v 3   # full suite
```
