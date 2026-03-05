---
trigger: glob
glob: "**/signals.py"
---

# Django Signal Conventions

## Guard Conditions — Be Explicit and Consistent

Every signal handler that creates resources scoped to an account MUST guard on:

1. **Account status** — always check `account.status == Account.Status.ACTIVE` before creating any sub-resource (ServiceImporter, ServiceAccount, etc.)
2. **Required flags** — check all prerequisite boolean flags (e.g. `uac_enabled`, `uac_google_ads_enabled`)
3. **Required FK/field presence** — check non-nullable fields that might still be logically absent (e.g. `customer_id is not None`)

```python
# BAD — skips account status check; creates SI for inactive accounts
@receiver(models.signals.post_save, sender=SharedCredentials)
def create_uac_adjust_importer(instance: SharedCredentials, *args, **kwargs):
    if 'adjust' not in instance.name.lower():
        return
    _create_service_importer(instance.account, ...)

# GOOD — guards status before delegating
@receiver(models.signals.post_save, sender=SharedCredentials)
def create_uac_adjust_importer(instance: SharedCredentials, *args, **kwargs):
    if 'adjust' not in instance.name.lower():
        return
    account = instance.account
    if account.status != Account.Status.ACTIVE:
        return
    _create_service_importer(account, ...)
```

All parallel signal handlers for the same use case (e.g. Google Ads, Facebook Ads, Adjust, TikTok UAC importers) MUST apply the **same set of guards** — inconsistency between handlers is a bug.

## Exception Handling — Handle All or Handle None

Every `.get()` call that can raise `DoesNotExist` MUST be handled consistently within the same signal:

```python
# BAD — Importer.DoesNotExist is caught, but BusinessModel.DoesNotExist is not
try:
    importer = Importer.objects.get(importer_class=MY_CLASS)
except Importer.DoesNotExist:
    return
anymind_bm = BusinessModel.objects.get(id=BUSINESS_MODEL_ANYMIND_ID)  # unhandled!

# GOOD — all lookups that can fail are wrapped together
try:
    importer = Importer.objects.get(importer_class=MY_CLASS)
    anymind_bm = BusinessModel.objects.get(id=BUSINESS_MODEL_ANYMIND_ID)
    service = Service.objects.get(id=SERVICE_ID)
except (Importer.DoesNotExist, BusinessModel.DoesNotExist, Service.DoesNotExist):
    return
```

Unhandled `DoesNotExist` in a signal propagates up and aborts the `save()` that triggered it — a silent data corruption risk.

## Performance — Hoist Constant DB Lookups Outside Loops

Never query the same constant record inside a loop. Hoist it above:

```python
# BAD — queries BusinessModel on every loop iteration
for importer_class, suffix in IMPORTER_CONFIGS:
    bm = BusinessModel.objects.get(id=BUSINESS_MODEL_ANYMIND_ID)
    ServiceAccount.objects.get_or_create(..., defaults={'business_model': bm})

# GOOD — one query, reused across iterations
bm = BusinessModel.objects.get(id=BUSINESS_MODEL_ANYMIND_ID)
for importer_class, suffix in IMPORTER_CONFIGS:
    ServiceAccount.objects.get_or_create(..., defaults={'business_model': bm})
```

## Idempotency — Always Use get_or_create

Signals may fire multiple times (e.g. every save, not just creation). Never use `create()` — always `get_or_create()` so re-runs are safe:

```python
# BAD
ServiceImporter.objects.create(service_account=sa, importer=importer, ...)

# GOOD
ServiceImporter.objects.get_or_create(
    service_account=sa,
    importer=importer,
    defaults={...},
)
```

## Reverse Relation Access

Accessing a `OneToOneField` reverse accessor (e.g. `gam_account.account`) raises `ModelClass.DoesNotExist` when no related object exists — always wrap it:

```python
try:
    account = instance.account
except Account.DoesNotExist:
    return
```
