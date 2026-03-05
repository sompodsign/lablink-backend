# Database Query Helper

Use the PostgreSQL MCP server (`mcp__postgres__query`) for all database queries.

**Database**: `adpp_db` | **Schema**: `adpp_db`
**Important**: Always prefix tables with `adpp_db.` (e.g., `SELECT * FROM adpp_db.core_account`)

## Schema Reference — MANDATORY

**BEFORE writing ANY SQL query**, you MUST read `.claude/skills/sync-db-schema/schema-reference.md` to verify the exact column names for every table you reference. NEVER guess or assume column names — always confirm them from the schema file first.

To refresh the schema from the live database, run the `/sync-db-schema` skill.

## Quick Reference — Key Tables

| Table | Purpose |
|-------|---------|
| `core_account` | Publisher/admin accounts |
| `core_user` | User accounts |
| `apps_site` | Publisher websites |
| `apps_app` | Mobile applications |
| `apps_service_importer` | Revenue importer configs |
| `apps_importer` | Importer type definitions |
| `apps_service_account` | Account ↔ service links |
| `apps_service` | Ad services/networks |
| `apps_third_party_tag` | Importer ↔ ad unit mappings |
| `apps_report` | Revenue reports (partitioned by month) |
| `ads_ad_unit` | GAM/AdMob ad units |
| `ads_order` | GAM orders |
| `ats_prebid_bidder` | Header bidding partners |
| `ats_site_setting` | ATS config per site |
| `ats_version` | ATS build versions |

## Common Queries

### Get Account with Related Data
```sql
SELECT a.id, a.name, a.type, a.status, a.owner_id,
       o.name as owner_name, a.country, a.currency
FROM adpp_db.core_account a
LEFT JOIN adpp_db.core_account o ON a.owner_id = o.id
WHERE a.id = <ACCOUNT_ID>;
```

### Get Sites for Account
```sql
SELECT s.id, s.name, s.host_names, s.ats_enabled, s.pwa_enabled
FROM adpp_db.apps_site s
WHERE s.account_id = <ACCOUNT_ID> AND s.is_deleted = false;
```

### Get Service Importer with Account
```sql
SELECT si.id, si.name, si.is_active, si.last_import_status,
       si.last_import_datetime, sa.name as service_account,
       a.name as account_name, s.name as service_name
FROM adpp_db.apps_service_importer si
JOIN adpp_db.apps_service_account sa ON si.service_account_id = sa.id
JOIN adpp_db.core_account a ON sa.account_id = a.id
JOIN adpp_db.apps_service s ON sa.service_id = s.id
WHERE si.id = <IMPORTER_ID>;
```

### Get Report Summary by Date Range
```sql
SELECT date, SUM(imp) as impressions, SUM(total_revenue) as revenue
FROM adpp_db.apps_report_y2024m01  -- Use correct partition
WHERE third_party_tag_id IN (
    SELECT tpt.id FROM adpp_db.apps_third_party_tag tpt
    JOIN adpp_db.apps_service_account sa ON tpt.service_account_id = sa.id
    WHERE sa.account_id = <ACCOUNT_ID>
)
GROUP BY date ORDER BY date;
```

### Get Prebid Bidder with Service
```sql
SELECT b.id, b.code, b.name, b.enable_header_bidding_automation,
       b.header_bidding_class, sa.name as service_account_name
FROM adpp_db.ats_prebid_bidder b
JOIN adpp_db.apps_service_account sa ON b.service_account_id = sa.id
WHERE b.id = <BIDDER_ID>;
```

## Notes

- **Encrypted fields**: `_account_info`, `_credential`, `_header_bidding_credentials` — cannot be read via SQL
- **Historical tables**: `{table}_historical` for audit trail (django-simple-history)
- **Partitioned tables**: Reports partitioned by month — always specify correct partition
- **Read-only**: Use SELECT only unless explicitly asked to modify data
