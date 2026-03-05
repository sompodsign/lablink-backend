---
name: sync-db-schema
description: Fetch the current database schema from PostgreSQL and update the schema reference file. Use when the database schema has changed (new migrations applied), when the schema feels outdated, or periodically to keep it current.
---

# Sync Database Schema

Query the live PostgreSQL database and regenerate `.claude/skills/sync-db-schema/schema-reference.md` with the current schema.

## Instructions

### Step 1: Fetch All Tables

Use `mcp__postgres__query` to get all non-historical, non-partitioned tables:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'adpp_db'
  AND table_type = 'BASE TABLE'
  AND table_name NOT LIKE '%_historical'
  AND table_name NOT LIKE '%_y____m__'
  AND table_name NOT LIKE 'django_%'
  AND table_name NOT LIKE 'auth_%'
  AND table_name NOT LIKE 'celery_%'
ORDER BY table_name;
```

### Step 2: Group Tables by Prefix

Group the tables by their prefix into sections:

| Prefix | Section Name |
|--------|-------------|
| `core_` | Core Tables |
| `apps_` | App Tables |
| `ats_` | ATS (Ad Tag System) Tables |
| `ads_` | Ad Unit & Order Tables |
| `admob_` | AdMob Tables |
| `pwa_` | PWA Tables |
| `amp_` | AMP Tables |
| Other | Other Tables |

### Step 3: Fetch Column Details for Each Table

For each table, query its columns:

```sql
SELECT
    c.column_name,
    c.data_type,
    c.is_nullable,
    c.column_default,
    c.character_maximum_length,
    CASE
        WHEN pk.column_name IS NOT NULL THEN 'PK'
        WHEN fk.column_name IS NOT NULL THEN 'FK → ' || fk.foreign_table_name
        ELSE ''
    END AS key_info
FROM information_schema.columns c
LEFT JOIN (
    SELECT kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    WHERE tc.table_name = '<TABLE_NAME>'
        AND tc.table_schema = 'adpp_db'
        AND tc.constraint_type = 'PRIMARY KEY'
) pk ON c.column_name = pk.column_name
LEFT JOIN (
    SELECT
        kcu.column_name,
        ccu.table_name AS foreign_table_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage ccu
        ON tc.constraint_name = ccu.constraint_name
        AND tc.table_schema = ccu.table_schema
    WHERE tc.table_name = '<TABLE_NAME>'
        AND tc.table_schema = 'adpp_db'
        AND tc.constraint_type = 'FOREIGN KEY'
) fk ON c.column_name = fk.column_name
WHERE c.table_name = '<TABLE_NAME>'
    AND c.table_schema = 'adpp_db'
ORDER BY c.ordinal_position;
```

IMPORTANT: Do NOT query all tables at once. Process them in batches of 5-10 tables per query to avoid overwhelming the context. Prioritize the most important tables first:

**Priority 1** (always include full columns):
`core_account`, `core_user`, `apps_site`, `apps_app`, `apps_service_importer`, `apps_report`, `ads_ad_unit`, `ads_order`, `ats_prebid_bidder`, `ats_site_setting`

**Priority 2** (include full columns):
All remaining `core_`, `apps_`, `ats_`, `ads_` tables

**Priority 3** (table name + column count only):
`admob_`, `pwa_`, `amp_`, and other less-used tables

### Step 4: Fetch Indexes

For important tables, also query indexes:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'adpp_db'
    AND tablename = '<TABLE_NAME>'
    AND indexname NOT LIKE '%_pkey'
ORDER BY indexname;
```

### Step 5: Generate schema-reference.md

Write the updated schema to `.claude/skills/sync-db-schema/schema-reference.md` following this format:

```markdown
# Database Schema Reference

This command provides database schema details for the ADPP backend. Use the PostgreSQL MCP server (`mcp__postgres__query`) for all database queries.

**Database**: `adpp_db` | **Schema**: `adpp_db`
**Important**: Always prefix tables with `adpp_db.` (e.g., `SELECT * FROM adpp_db.core_account`)
**Last synced**: <CURRENT_DATE>

---

## Table Naming Conventions

| Prefix | Domain | Examples |
|--------|--------|----------|
| `core_` | Core models | `core_account`, `core_user` |
| `apps_` | Feature apps | `apps_site`, `apps_service_importer` |
| ... | ... | ... |

**Historical tables**: `{table_name}_historical`
**Partitioned reports**: `{table_name}_y{year}m{month}`

---

## Core Tables

### core_account
<description>

| Column | Type | Key Info |
|--------|------|----------|
| `id` | integer | PK |
| `name` | text | Account name |
| `owner_id` | integer | FK → core_account |
...
```

### Step 6: Report Summary

After updating, report:
- Total tables found
- Tables with full schema documented
- Tables with summary only
- New tables found (not in previous schema-reference.md)
- Removed tables (in previous schema-reference.md but no longer in database)

## Important Notes

- Use `mcp__postgres__query` for all database queries
- Always use `adpp_db` schema prefix in queries
- Skip `django_*`, `auth_*`, `celery_*` internal tables
- Skip `*_historical` tables (auto-generated by django-simple-history)
- Skip `*_y{year}m{month}` partitioned tables
- Add `**Last synced**: <date>` header so we know when it was last updated
- Keep the file under 500 lines — use summary format for low-priority tables
