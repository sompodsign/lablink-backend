# Quality Command

**Command**: `/quality`

**Purpose**: Comprehensive code quality check, auto-fix, and re-check workflow

**Description**: Runs a complete code quality pipeline: check -> fix -> re-check. Don't create todo list.

## Workflow

**MANDATORY**: Must execute ALL steps in sequence. If fixes are applied, re-run checks to verify.

### Phase 1: Initial Checks

```bash
echo "=== PHASE 1: INITIAL CHECKS ==="

echo "1. Checking formatting..."
poetry run poe format_check

echo "2. Checking linting rules..."
poetry run poe ruff_check

echo "3. Running type checks..."
poetry run poe mypy
```

### Phase 2: Auto-Fix (if any checks failed)

```bash
echo "=== PHASE 2: AUTO-FIX ==="

echo "1. Auto-fixing formatting..."
poetry run poe format

echo "2. Auto-fixing linting issues..."
poetry run poe ruff_fix
```

### Phase 3: Re-Check (verify fixes)

```bash
echo "=== PHASE 3: RE-CHECK ==="

echo "1. Re-checking formatting..."
poetry run poe format_check

echo "2. Re-checking linting rules..."
poetry run poe ruff_check

echo "3. Re-running type checks..."
poetry run poe mypy
```

## Instructions for Claude Code

1. **Run Phase 1** - Execute all three checks
2. **If ALL pass** - Report success, skip to exit
3. **If ANY fail** - Run Phase 2 (auto-fix)
4. **After fixes** - Run Phase 3 (re-check)
5. **If re-checks pass** - Report success
6. **If re-checks fail** - Report remaining issues that need manual intervention

**Important:**
- Run each command individually using the Bash tool
- Track which checks pass/fail
- Only run Phase 2 if Phase 1 has failures
- Always run Phase 3 after Phase 2

## Exit Behavior

- **SUCCESS**: All checks pass (either in Phase 1 or Phase 3)
- **FIXED**: Some issues auto-fixed, all re-checks pass
- **FAILED**: Issues remain after auto-fix, manual intervention required

## Return Value

When used by other commands (like `/pr`), this command should:
- Return success if all checks pass
- Return failure if any checks fail after auto-fix attempt
