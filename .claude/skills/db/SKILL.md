---
name: db
description: Read-only Postgres investigation for application data and schema analysis. Use when users ask to check database records, verify counts, inspect schema/tables/columns/foreign keys, validate joins, debug data mismatches, or answer questions that require SQL against a live database.
---

# DB

## Workflow
1. Confirm the target database/connection context.
2. Load `references/query-playbook.md` for query style and safety rules.
3. Use `references/thai-learning-schema.md` for quick table/column lookup.
4. Run schema discovery from `references/schema-introspection.sql` when live DB shape must be confirmed.
5. Write and execute read-only SQL.
6. Return results with:
- SQL used
- assumptions made
- caveats (stale schema snapshot, missing table, permission issue)

## Query Standards
- Prefer read-only SQL (`SELECT` / CTEs ending in `SELECT`).
- Avoid `SELECT *` unless exploring unknown data.
- Add `LIMIT` for exploratory queries.
- Use explicit `ORDER BY` for deterministic output.
- Use `COUNT(DISTINCT ...)` when joins can duplicate rows.

## Schema Sources
- `references/thai-learning-schema.md`: Snapshot generated from Django model metadata.
- `references/schema-introspection.sql`: Canonical live Postgres introspection queries.

If live DB access fails (missing DB, bad credentials, unavailable server), use the schema snapshot and report the exact connection error.

## Refresh Snapshot
Run when backend models changed:

```bash
~/.codex/skills/db/scripts/refresh_schema_snapshot.sh
```
