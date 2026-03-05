---
name: db
description: Read-only Postgres investigation for application data and schema analysis. Use when users ask to check database records, verify counts, inspect schema/tables/columns/foreign keys, validate joins, debug data mismatches, or answer questions that require SQL against a live database.
---

# DB

## Workflow
1. Confirm the target database/connection context.
2. Load `references/query-playbook.md` for query style and safety rules.
3. Load `references/thai-learning-schema.md` for quick table/column lookup.
4. Run schema discovery from `references/schema-introspection.sql` when live DB shape must be confirmed.
5. Write and execute read-only SQL.
6. Return results with SQL used, assumptions made, and caveats.

## Query Standards
- Prefer read-only SQL (`SELECT` / CTEs ending in `SELECT`).
- Avoid `SELECT *` unless exploring unknown data.
- Add `LIMIT` for exploratory queries.
- Use explicit `ORDER BY` for deterministic output.
- Use `COUNT(DISTINCT ...)` when joins can duplicate rows.

## Refresh Snapshot
Run when backend models changed:
```bash
.agents/skills/db/scripts/refresh_schema_snapshot.sh
```
