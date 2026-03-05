---
trigger: glob
glob: "**/*.py"
---

# Security Rules

## Credentials & Secrets

- NEVER hardcode credentials, API keys, tokens, or secrets in code
- NEVER log `_account_info` values, passwords, or token content
- Use `CredentialsField` (from `src.fields`) for encrypted credential storage
- Mask credentials in any output — show first 4 chars only: `api_key[:4]...`

## Database Queries

- Use Django ORM for queries — avoid raw SQL unless absolutely necessary
- Raw SQL MUST use parameterized queries with `%s` placeholders:

  ```python
  # CORRECT
  cursor.execute("SELECT * FROM table WHERE id = %s", [user_id])

  # WRONG — SQL injection risk
  cursor.execute(f"SELECT * FROM table WHERE id = {user_id}")
  ```

## Input Validation

- Validate and sanitize all user input before database queries
- Use Django forms, serializers, or Pydantic models for input validation
- Never trust client-side validation alone

## Authentication & Authorization

- Every API endpoint MUST have permission checks
- REST: use DRF permission classes
- GraphQL: use `extensions=[IsStaffUser(fail_silently=False)]` on every query/mutation
- Graphene (legacy): use `@login_required` decorator

## Encrypted Fields

- `CredentialsField` encrypts with the server's SECRET_KEY
- NEVER use `filter().update()` or `si.account_info = {...}; si.save()` from local development — encrypts with wrong SECRET_KEY
- Use raw SQL to copy encrypted blobs between environments (see credential-restore skill)
