# Django Shell Code Runner

Search for a code snippet in the codebase by message/keyword and execute it in Django shell.

**Argument**: $ARGUMENTS - The search term/message to find in the codebase

## Common Commands Reference

When the user's request matches one of these common commands, execute it directly without searching.

### ATS Bidder Tasks

**Update ATS Prebid Bidder** (sync bidder sites and ad units):
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell <<'EOF'
from src.apps.ats.tasks import update_bidder
update_bidder(bidder_id=<BIDDER_ID>)
EOF
```

**Bulk Update All ATS Bidders**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell <<'EOF'
from src.apps.ats.tasks import bulk_update_bidder_task
bulk_update_bidder_task.run()
EOF
```

**Update Bidder Ad Sizes**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell <<'EOF'
from src.apps.ats.tasks import update_bidder_ad_size
update_bidder_ad_size.run()  # All bidders
# OR for specific bidder code:
update_bidder_ad_size.run(bidder_code='<BIDDER_CODE>')
EOF
```

**Map Bidder Site via GAM Ad Unit Path**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell <<'EOF'
from src.apps.ats.tasks import map_bidder_site_and_bidder_ad_unit_via_gam_ad_unit_path_task
map_bidder_site_and_bidder_ad_unit_via_gam_ad_unit_path_task(ats_prebid_bidder_id=<BIDDER_ID>)
EOF
```

### AdMob Mediation Bidder Tasks

**Update Mediation Bidder** (sync bidder apps and ad units):
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell <<'EOF'
from src.apps.admob.tasks import update_mediation_bidder
update_mediation_bidder(bidder_id=<BIDDER_ID>)
EOF
```

**Bulk Update All Mediation Bidders**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell <<'EOF'
from src.apps.admob.tasks import bulk_update_mediation_bidder_task
bulk_update_mediation_bidder_task.run()
EOF
```

**Sync AdMob Ad Sources**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell <<'EOF'
from src.apps.admob.tasks import sync_admob_ad_source_task
sync_admob_ad_source_task.run()
EOF
```

**Sync AdMob Ad Source for Account**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell <<'EOF'
from src.apps.admob.tasks import sync_admob_ad_source_account_task
sync_admob_ad_source_account_task.run(account_id=<ACCOUNT_ID>)
EOF
```

**Sync AdMob Mediation Groups**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell <<'EOF'
from src.apps.admob.tasks import sync_admob_mediation_groups_task
sync_admob_mediation_groups_task.run(account_id=<ACCOUNT_ID>)  # or None for all
EOF
```

### Service Importer Commands (Debug Importers)

**Execute Service Importer by ID** (management command):
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py execute_service_import --ids <IMPORTER_ID> --force
```

**Execute Service Importer with Date Range**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py execute_service_import --ids <IMPORTER_ID> --start_date 2024-01-01 --end_date 2024-01-31 --force
```

**Execute All Importers for an Account**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py execute_service_import --account_ids <ACCOUNT_ID> --force
```

**Execute Importers by Service Account ID**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py execute_service_import --service_account_ids <SERVICE_ACCOUNT_ID> --force
```

### Model Queries

**Get Account Info**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell -c "from src.core.account.models import Account; print(Account.objects.get(id=<ACCOUNT_ID>))"
```

**Get ATS Prebid Bidder Info**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell -c "from src.apps.ats.models import AtsPrebidBidder; b = AtsPrebidBidder.objects.get(id=<ID>); print(f'Name: {b.name}, Code: {b.code}, Enabled: {b.enable_header_bidding_automation}')"
```

**Get Service Importer Info**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell -c "from src.apps.importer.models import ServiceImporter; si = ServiceImporter.objects.get(id=<ID>); print(f'Name: {si.name}, Active: {si.is_active}, Account: {si.service_account.account}')"
```

**Get Mediation Bidder Info**:
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell -c "from src.apps.admob.models import MediationBidder; b = MediationBidder.objects.get(id=<ID>); print(f'Name: {b.name}, Ad Source: {b.ad_source}')"
```

### Async Task Execution (Queue via Celery)

To queue tasks asynchronously instead of running synchronously, use `.delay()`:
```python
update_bidder.delay(bidder_id=<BIDDER_ID>)  # Queued
update_mediation_bidder.delay(bidder_id=<BIDDER_ID>)  # Queued
```

---

## Instructions (For Custom Searches)

If the user's request doesn't match a common command above, follow these steps:

1. **Search for the code snippet** in the codebase using the provided argument `$ARGUMENTS`
   - Search in Python files (`*.py`) for the message/keyword
   - Look for comments, docstrings, function names, or code containing the search term
   - Prioritize executable code blocks (functions, classes, or standalone code)

2. **Identify the relevant code** to execute
   - If a function/method is found, prepare to call it
   - If a code block is found, prepare to execute it
   - If multiple matches exist, show them to the user and ask which one to run

3. **Execute in Django shell** using the following command:
   ```bash
   cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell -c "<code_to_execute>"
   ```

   For multi-line code, use a heredoc:
   ```bash
   cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell <<'EOF'
   <multi_line_code>
   EOF
   ```

4. **Display the results** to the user

## Examples

**Search for and run code related to "account cleanup":**
```bash
# First search for the code
grep -r "account cleanup" --include="*.py" .

# Then execute the found function in Django shell
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell -c "from src.core.account.utils import cleanup_accounts; cleanup_accounts()"
```

**Run a specific model query:**
```bash
cd adpp_backend && ENV_PATH=./.env poetry run python manage.py shell -c "from src.core.account.models import Account; print(Account.objects.count())"
```

## Notes

- Always import necessary modules before executing code
- Be cautious with code that modifies data - confirm with user first
- Show the code that will be executed before running it
- Display both stdout and any errors from execution
- For encrypted credential fields, you may encounter `BadSignature` errors if local env keys differ from production
