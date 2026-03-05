# DB Query Playbook

## Fast Workflow
1. Confirm the target DB connection and scope.
2. Inspect schema first:
- Use `thai-learning-schema.md` for baseline table/column names.
- Use `schema-introspection.sql` to verify live schema.
3. Write a read-only query with explicit columns and a `LIMIT` when applicable.
4. Run query.
5. Validate result shape and edge cases (`NULL`, missing joins, timezone/date filters).
6. Return answer with SQL used and assumptions.

## Query Rules
- Prefer read-only SQL (`SELECT`, CTEs ending in `SELECT`).
- Avoid `SELECT *` unless debugging unknown shape.
- Add `LIMIT 50` for exploratory checks.
- Use explicit `ORDER BY` for deterministic output.
- For counts across joins, verify duplication risk and use `COUNT(DISTINCT ...)` when needed.

## Thai Learning Domain Pointers
- Todos: `todos_todo`, `todos_subtask`, `todos_tododetail`, `todos_project`, `todos_note`
- Vocabulary: `vocabulary_word`, `vocabulary_meaning`, `vocabulary_example`, `vocabulary_phrase`, `vocabulary_userword`
- Lessons: `lessons_lesson`, `lessons_lessoncategory`, `lessons_lessontemplate`
- Finance: `finance_agreement`, `finance_budget`, `finance_budget_item`, `finance_earning`, `finance_repayment`
- Auth/User: `auth_user`, `users_profile`

## Common Checks

### Find rows by date range
```sql
SELECT id, created_at
FROM some_table
WHERE created_at >= DATE '2026-01-01'
  AND created_at < DATE '2026-02-01'
ORDER BY created_at DESC
LIMIT 50;
```

### Verify child records exist for parent rows
```sql
SELECT p.id, p.title, COUNT(c.id) AS child_count
FROM parent_table p
LEFT JOIN child_table c ON c.parent_id = p.id
GROUP BY p.id, p.title
ORDER BY child_count ASC, p.id ASC;
```

### Check data quality for null/blank
```sql
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE some_col IS NULL) AS null_count,
  COUNT(*) FILTER (WHERE TRIM(COALESCE(some_text, '')) = '') AS blank_count
FROM some_table;
```
