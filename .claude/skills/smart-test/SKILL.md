---
name: smart-test
description: Automatically find and run the right tests for changed files in the ADPP backend. Use when you want to run tests after making code changes, to verify your changes don't break anything, or to find which tests cover specific code.
---

# Smart Test Runner

Automatically determine which tests to run based on changed files and execute them.

## Arguments

`$ARGUMENTS` — optional: specific file path, app name, or "all" to run the full suite.

## Instructions

### Step 1: Identify Changed Files

```bash
# Files changed in current branch vs master
git diff --name-only origin/master...HEAD -- '*.py' | grep -v '/migrations/'
```

### Step 2: Map Files to Tests

Use these mapping rules:

| Changed File Pattern | Test Location |
|---------------------|---------------|
| `src/apps/<app>/models.py` | `src/apps/<app>/tests/` |
| `src/apps/<app>/views.py` | `src/apps/<app>/tests/` |
| `src/apps/<app>/graphql/` | `src/apps/<app>/tests/` |
| `src/apps/importer/modules/service/importers/<name>/main.py` | `src/apps/importer/modules/service/importers/<name>/tests.py` |
| `src/core/<module>/models.py` | `src/core/<module>/tests/` |
| `libs/<lib>/` | `libs/<lib>/tests/` |
| `src/utils/<util>/` | `src/utils/<util>/tests/` |

### Step 3: Check for Test Files

For each mapped test path, verify the file/directory exists:
```bash
ls adpp_backend/<test_path> 2>/dev/null
```

### Step 4: Run Tests

```bash
ENV_PATH=./adpp_backend/env/test.env-unit-test.yaml poetry run coverage run ./adpp_backend/manage.py test -d ./adpp_backend/<test_path> --keepdb -v 3
```

For importer tests (tagged, normally excluded):
```bash
ENV_PATH=./adpp_backend/env/test.env-unit-test.yaml poetry run coverage run ./adpp_backend/manage.py test -d ./adpp_backend/<test_path> --keepdb -v 3 --tag=importer
```

### Step 5: Report Results

```
## Test Results

### Files Changed: <count>
<list of changed files>

### Tests Run: <count>
<list of test files/classes>

### Results:
- Passed: <count>
- Failed: <count>
- Errors: <count>
- Skipped: <count>

### Failed Tests:
<details for each failure>
```

## Special Cases

- **Importer files**: Tests are tagged with `@tag('importer')` — use `--tag=importer` flag
- **No test file found**: Warn the user that no tests exist for the changed file
- **Multiple apps changed**: Run tests for each app separately to isolate failures
- **GraphQL changes**: Also run any `test_graphql*.py` files in the app
- **Full suite**: Use `poetry run poe coverage` for the complete test run

## Prerequisites

Ensure PostgreSQL is running:
```bash
docker-compose up -d postgres
```

Local database: `localhost:5433`, database: `adpp_db`, user: `adpp_admin`
