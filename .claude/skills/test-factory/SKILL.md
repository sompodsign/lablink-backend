---
name: test-factory
description: Generate Factory Boy factory classes for ADPP Django models. Use when writing tests that need test data, when a model doesn't have a factory yet, or when existing factories need updating after model changes.
---

# Factory Boy Factory Generator

Generate Factory Boy factory classes that match ADPP model definitions.

## Arguments

`$ARGUMENTS` — the model name or file path (e.g., `Account`, `ServiceImporter`, `src/core/account/models.py`).

## Instructions

### Step 1: Read the Model

Find and read the model definition:
```bash
grep -r "class <ModelName>" adpp_backend/src/ --include="*.py" -l
```

Read the model file to understand all fields, their types, defaults, and relationships.

### Step 2: Check for Existing Factory

```bash
grep -r "class <ModelName>Factory" adpp_backend/ --include="*.py" -l
```

If a factory already exists, read it and suggest updates for any new/changed fields.

### Step 3: Generate Factory

Follow ADPP conventions:

```python
import factory
from factory.django import DjangoModelFactory

from <model_import_path> import <ModelName>


class <ModelName>Factory(DjangoModelFactory):
    class Meta:
        model = <ModelName>

    # CharField / TextField
    name = factory.Faker('name')

    # IntegerField
    count = factory.Faker('random_int', min=0, max=100)

    # DecimalField (for revenue)
    revenue = factory.LazyFunction(lambda: Decimal('100.00'))

    # BooleanField
    is_active = True

    # ForeignKey
    account = factory.SubFactory(AccountFactory)

    # DateTimeField
    created_at = factory.LazyFunction(timezone.now)

    # Encrypted fields (like _account_info)
    # Use factory.LazyAttribute for complex defaults

    # ArrayField
    host_names = factory.LazyFunction(lambda: ['example.com'])
```

### Step 4: Place the Factory

Factory files go in:
- `adpp_backend/src/apps/<app>/factories.py` — for app models
- `adpp_backend/src/core/<module>/factories.py` — for core models
- Same file as existing factories if one exists

### ADPP-Specific Patterns

1. **ServiceImporterFactory**: Already exists at `src/apps/importer/factories.py` — accepts `account_info` dict
2. **AccountFactory**: Core factory, used extensively — check `src/core/account/factories.py`
3. **UserFactory**: Used for authenticated API tests — check `src/core/user/factories.py`
4. **Encrypted fields**: Use plain dict values — Django encrypts on save
5. **Status fields**: Use model constants (e.g., `Account.Status.ACTIVE`)
6. **ForeignKey with specific values**: Use `factory.SubFactory` with params

### Testing the Factory

After generating, verify:
```python
# In Django shell
from <factory_path> import <ModelName>Factory
obj = <ModelName>Factory()
print(obj.id, obj.name)  # Should create successfully
```
