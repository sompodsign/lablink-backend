# Run Task-Related Unit Tests

Run unit tests for code modified during the current task using the local test environment.

## Instructions

1. **Identify changed files** from the current task/branch
2. **Find corresponding test files** for the modified code
3. **Run the relevant tests** using the test environment configuration

### Test Discovery Strategy

For each modified file, look for tests in:
- Same directory: `tests/` subfolder or `test_*.py` files
- App-level: `tl-be/apps/<app_name>/tests/`
- Shared-level: `tl-be/shared/tests/`

### Run Command

```bash
cd tl-be && ENV_PATH=./env.test poetry run coverage run manage.py test <test_path> --keepdb -v 3
```

### Examples

**Run tests for a specific app:**
```bash
cd tl-be && ENV_PATH=./env.test poetry run coverage run manage.py test apps.lessons --keepdb -v 3
```

**Run tests for a specific test class:**
```bash
cd tl-be && ENV_PATH=./env.test poetry run coverage run manage.py test apps.lessons.tests.test_models.LessonTestCase --keepdb -v 3
```

**Run a single test method:**
```bash
cd tl-be && ENV_PATH=./env.test poetry run coverage run manage.py test apps.lessons.tests.test_models.LessonTestCase.test_create --keepdb -v 3
```

**Run all tests (full suite):**
```bash
cd tl-be && ENV_PATH=./env.test poetry run coverage run manage.py test --keepdb -v 3
```

## Test Environment

Make sure you have the test environment file configured at `tl-be/env.test`
