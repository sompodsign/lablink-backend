---
description: Comprehensive code quality check, auto-fix, and re-check workflow
---

# Quality Check

**MANDATORY**: Execute ALL steps in sequence.

### Phase 1: Initial Checks
```bash
poetry run poe format_check
poetry run poe ruff_check
poetry run poe mypy
```

### Phase 2: Auto-Fix (if any checks failed)
```bash
poetry run poe format
poetry run poe ruff_fix
```

### Phase 3: Re-Check (verify fixes)
```bash
poetry run poe format_check
poetry run poe ruff_check
poetry run poe mypy
```

- If ALL pass in Phase 1 → report success
- If ANY fail → run Phase 2 then Phase 3
- If Phase 3 still fails → report remaining issues
