---
name: migration-check
description: Check Django migrations for safety and correctness after model changes. Use when models are modified, new migrations are created, or before merging PRs with migration files. Detects conflicts, data loss risks, and lock contention issues.
---

# Django Migration Safety Check

Analyze Django migration files for safety issues before they reach production.

## Arguments

`$ARGUMENTS` — optional path to a specific migration file or app name.

## Instructions

### Step 1: Identify Migration Changes

Find new or modified migration files:
```bash
git diff --name-only origin/master...HEAD -- '*.py' | grep '/migrations/'
```

If no argument provided, check all migrations changed in the current branch.

### Step 2: Safety Checks

For each migration file, verify:

#### Data Loss Detection
- `RemoveField` — warn if field contains data (check if it's nullable or has a default)
- `DeleteModel` — CRITICAL: verify no ForeignKey references exist
- `AlterField` reducing size (e.g., `CharField(max_length=100)` → `CharField(max_length=50)`)
- `RunSQL` with destructive statements (`DROP`, `DELETE`, `TRUNCATE`)

#### Lock Contention
- `AddIndex` on large tables (check if table has partitioned reports: `apps_report_y*`)
- `AlterField` on tables with millions of rows (core_account, apps_site, apps_report)
- `AddField` with `NOT NULL` and no default on existing tables — requires `DEFAULT` or nullable first

#### Conflict Detection
```bash
# Check for migration number conflicts with master
python adpp_backend/manage.py showmigrations --plan | grep -E '\[ \]'
```

#### Dependency Verification
- Ensure `dependencies` list includes the correct previous migration
- Check for circular dependencies across apps
- Verify `run_before` constraints if present

### Step 3: Historical Table Impact

ADPP uses `django-simple-history`. If a model has `historical = True`:
- The migration will also affect `<table>_historical`
- Historical tables can be very large — flag performance concerns
- Verify historical tracking isn't accidentally disabled

### Step 4: Naming Convention Check

- Migration files should have descriptive names, not auto-generated ones
- Convention: `NNNN_<descriptive_action>.py` (e.g., `0042_add_slot_name_field.py`)

### Step 5: Report

Output a structured report:
- **SAFE**: Migrations that are safe to apply
- **WARNING**: Migrations that need review (potential performance impact)
- **DANGEROUS**: Migrations that could cause data loss or extended locks
- **CONFLICT**: Migration number conflicts with existing branches

## Important Notes

- ADPP uses PostgreSQL — some operations are safe in PostgreSQL that aren't in MySQL (e.g., `ADD COLUMN` is fast)
- Partitioned report tables (`apps_report_y{year}m{month}`) are very large — any migration touching these needs extra care
- Always check if `--fake` migration is needed for partitioned tables
- The `adpp_db` schema prefix is required in raw SQL migrations
