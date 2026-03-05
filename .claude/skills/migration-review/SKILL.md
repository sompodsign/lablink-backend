---
name: migration-review
description: Review Django migration files for safety, performance, and correctness. Use when creating migrations, reviewing migration PRs, or before applying migrations to production. Checks for data loss, lock contention, and backward compatibility.
---

# Django Migration Review

Perform a thorough safety review of Django migration files.

## Arguments

`$ARGUMENTS` — optional: app name, migration file path, or "all" to check all pending migrations.

## Instructions

### Step 1: Find Migrations to Review

```bash
# All new/modified migrations on current branch
git diff --name-only origin/master...HEAD -- '*/migrations/*.py'
```

### Step 2: Read and Analyze Each Migration

For each migration file, read it and check for:

#### CRITICAL Issues (block deployment)

1. **Data-destroying operations**:
   - `migrations.DeleteModel` — verify the table is truly unused
   - `migrations.RemoveField` on non-nullable fields with data
   - `RunSQL` containing `DROP TABLE`, `DROP COLUMN`, `TRUNCATE`

2. **Long-running locks**:
   - `AddField` with `null=False` and no `default` — locks table while rewriting
   - `AddIndex` on tables > 1M rows without `CONCURRENTLY`
   - `AlterField` changing column type (requires table rewrite in PostgreSQL)

3. **Missing reverse migration**:
   - `RunPython` without `reverse_code` — makes rollback impossible

#### WARNING Issues (needs review)

1. **Large table operations**:
   - Any operation on `apps_report*` tables (partitioned, very large)
   - Any operation on `core_account`, `apps_site` (high-traffic tables)

2. **Index operations**:
   - New indexes on frequently-written tables
   - Composite indexes — verify column order matches query patterns

3. **Default values**:
   - `default=datetime.now` instead of `default=timezone.now`
   - Mutable defaults on model fields

#### INFO Items (good practices)

1. **Migration naming**: Should be descriptive (not `auto_20260228_0001`)
2. **Dependencies**: Correctly references previous migration
3. **Squash candidates**: Multiple small migrations that could be squashed

### Step 3: Check for Conflicts

```bash
# Check migration ordering
python adpp_backend/manage.py showmigrations <app_name> --plan 2>&1 | tail -20
```

### Step 4: Historical Table Impact

Check if the model uses `django-simple-history`:
```bash
grep -r "historical" adpp_backend/src/apps/<app>/models.py
```

If yes, warn that the migration will also modify the `*_historical` table.

### Step 5: Generate Report

```
## Migration Review: <migration_file>

### Safety Level: SAFE / WARNING / CRITICAL

### Operations:
1. <operation_type> — <description> — <safety_level>

### Recommendations:
- <recommendation>

### Rollback Plan:
- <steps to rollback if needed>
```

## PostgreSQL-Specific Notes

- `ADD COLUMN` with `NULL` default is fast (no table rewrite)
- `ADD COLUMN` with `NOT NULL` default requires table rewrite (Django 5+ handles this better)
- `CREATE INDEX CONCURRENTLY` doesn't lock the table but can't run in a transaction
- `ALTER TYPE` on a column requires full table rewrite
- ADPP uses `adpp_db` schema prefix in raw SQL
