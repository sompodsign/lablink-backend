-- Live Postgres schema introspection queries.
-- Run these with the postgres MCP query tool.

-- 1) List schemas
SELECT schema_name
FROM information_schema.schemata
ORDER BY schema_name;

-- 2) List base tables (non-system)
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_type = 'BASE TABLE'
  AND table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name;

-- 3) List columns for one table
-- Replace :schema_name and :table_name manually before running.
SELECT
  table_schema,
  table_name,
  ordinal_position,
  column_name,
  data_type,
  is_nullable,
  column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'todos_todo'
ORDER BY ordinal_position;

-- 4) List foreign keys
SELECT
  tc.table_schema,
  tc.table_name,
  kcu.column_name,
  ccu.table_schema AS foreign_table_schema,
  ccu.table_name AS foreign_table_name,
  ccu.column_name AS foreign_column_name,
  tc.constraint_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
 AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY tc.table_schema, tc.table_name, kcu.column_name;

-- 5) List indexes with definitions
SELECT
  schemaname,
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename, indexname;

-- 6) Approximate row counts (fast estimate)
SELECT
  schemaname,
  relname AS table_name,
  n_live_tup AS approx_rows
FROM pg_stat_user_tables
ORDER BY schemaname, relname;

-- 7) Exact row count for one table (can be expensive)
SELECT COUNT(*) AS exact_rows
FROM public.todos_todo;
