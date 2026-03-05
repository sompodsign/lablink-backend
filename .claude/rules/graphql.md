---
globs: "**/graphql/**"
---

# Strawberry GraphQL Conventions

## Framework

Use Strawberry (v2) for all new GraphQL code. Graphene is legacy — do not add new Graphene types.

## Permissions

EVERY query and mutation MUST have permission extensions:
```python
@strawberry.mutation(extensions=[IsStaffUser(fail_silently=False)])
```

NEVER expose data without authentication checks.

## Mutations

Always wrap in `@transaction.atomic` and return a response type:
```python
@strawberry.type
class MyMutationResponse:
    success: bool
    errors: Optional[GqlError] = None
    result: Optional[MyType] = None

@strawberry.mutation(extensions=[IsStaffUser(fail_silently=False)])
@transaction.atomic
def my_mutation(self, info, input: MyInput) -> MyMutationResponse:
    try:
        ...
    except ValidationError as e:
        transaction.set_rollback(True)
        return MyMutationResponse(success=False, errors=to_gql_validation_errors(e))
```

## Cache Invalidation

Mutations modifying cached models MUST include:
```python
@strawberry.mutation(metadata={INVALIDATION_MODELS_KEYS: [MyModel]})
```

## Decorators

- `@strawberry.input` for mutation inputs
- `@strawberry.type` for output types
- `@strawberry.enum` for enums (wrapping Python Enum)
- `@strawberry_django.type(Model)` for model-mapped types

## File Organization

```
graphql/v2/
├── types.py        # Output types
├── inputs.py       # Mutation inputs
├── queries.py      # Query resolvers
├── mutations.py    # Mutation resolvers
├── permissions.py  # Permission classes
├── validators.py   # Input validators
└── enums.py        # Enum types
```
