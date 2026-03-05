---
trigger: glob
glob: "**/migrations/*.py"
---

# Django Migration Rules

## Naming

Use descriptive names: `0042_add_slot_name_to_ad_unit.py`, NOT auto-generated `auto_20260228_0001.py`.

## Safety Checks

Before writing migrations, verify:

- `RemoveField` — confirm the field data is empty or migrated
- `DeleteModel` — confirm no ForeignKey references exist
- `AddField` with `null=False` — MUST provide a `default`, or make nullable first then backfill
- `RunSQL` with `DROP`, `DELETE`, `TRUNCATE` — these are IRREVERSIBLE
- `AlterField` changing column type — requires full table rewrite in PostgreSQL

## RunPython

Always include `reverse_code` for rollback support:

```python
migrations.RunPython(forward_func, reverse_func)
```

## Raw SQL

Always use the bare table name or default schema prefix:

```python
migrations.RunSQL("ALTER TABLE my_table ...")
```

## Historical Tables

Many models use `django-simple-history`. Migrations on these models ALSO affect `*_historical` tables. Be aware of:

- Double the table size impact
- Historical tables can be very large
- Excluded fields in `HistoricalRecords` won't be affected

## Large Tables — Extra Care

These tables are very large — migrations touching them need review:

- `apps_report_y{year}m{month}` (partitioned)
- `core_account`
- `apps_site`
- `apps_service_importer`

Consider: `CREATE INDEX CONCURRENTLY` (can't run in transaction), off-peak timing, maintenance windows.
