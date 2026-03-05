# Worktree Complete Ticket

Complete a Jira ticket end-to-end: fetch details, create a git worktree, implement the fix, run quality checks, commit, and push.

## Arguments

$ARGUMENTS - Jira ticket URL or ticket key (e.g., `ADPP-14416` or `https://anymindgroup.atlassian.net/browse/ADPP-14416`)

## Instructions

### Step 1: Parse Ticket Input

Extract the Jira ticket key from `$ARGUMENTS`:
- If a URL is provided, extract the ticket key from the path (e.g., `ADPP-14416` from `https://anymindgroup.atlassian.net/browse/ADPP-14416`)
- If a key is provided directly, use it as-is
- If no argument is provided, STOP and ask the user for a ticket key

### Step 2: Fetch Ticket Details from Jira

Use the Atlassian MCP tool `jira_get_issue` to fetch the ticket details:
- Get the issue summary, description, acceptance criteria, and any comments
- Understand the full scope of the issue before starting implementation
- Note the ticket key and summary for branch naming and commit messages

### Step 3: Ensure Clean State and Create Worktree

```bash
# Fetch latest from origin
git fetch origin

# Create a branch name from the ticket key and summary
# Format: ADPP-XXXXX-short-description (lowercase, hyphens)
TICKET_KEY="<ticket_key>"
BRANCH_NAME="<ticket_key>-<short-description>"

# Create worktree from master in ../adpp-backend-worktrees/<branch_name>
WORKTREE_DIR="../adpp-backend-worktrees/${BRANCH_NAME}"
mkdir -p ../adpp-backend-worktrees
git worktree add "${WORKTREE_DIR}" -b "${BRANCH_NAME}" origin/master
```

**IMPORTANT**: After creating the worktree, ALL subsequent file operations (reads, edits, writes, bash commands) MUST be performed inside the worktree directory (`${WORKTREE_DIR}`). Do NOT modify files in the main repository.

### Step 4: Implement the Fix

- Analyze the ticket details to understand the issue
- Explore the relevant code in the worktree
- Implement the fix following project coding standards and style guidelines defined in `CLAUDE.md` — this includes:
  - Single quotes for code, double quotes for docstrings only
  - SOLID principles, DRY, Gang of Four patterns where appropriate
  - `match`/`case` over if/elif chains
  - No nested try/except blocks
  - `logger.exception` instead of `logger.warning`
  - `itertuples(index=False)` over `iterrows()` for DataFrame iteration
  - Dataclasses/pydantic over other data structures where possible
  - Type hints for all new code
  - All imports at the top, ordered by convention
  - New functions go at the end of existing classes
- Keep changes minimal and focused on the ticket requirements
- Write unit tests if appropriate for the change (use your judgement), following CLAUDE.md testing conventions:
  - Use factories (never `objects.create`)
  - Inherit from test mixins (see `src.tests`)
  - Use `self.assert...` instead of bare `assert`

### Step 5: Run Quality Checks

Run quality checks inside the worktree:

```bash
cd "${WORKTREE_DIR}"

# Format check
poetry run poe format_check

# If formatting fails, auto-fix
poetry run poe format

# Lint check
poetry run poe ruff_check

# If linting fails, auto-fix
poetry run poe ruff_fix

# Type check
poetry run poe mypy
```

If quality checks fail after auto-fix, fix the remaining issues manually and re-run.

### Step 6: Run Related Tests

Run the `/test` command to discover and execute tests related to the modified files. The `/test` command will automatically identify changed files, find corresponding test files, and run them.

If any unit tests were written in Step 4, they will be picked up by `/test` as part of the changed files.

If tests fail, fix the issues and re-run `/test` until they pass.

### Step 7: Commit and Push

```bash
cd "${WORKTREE_DIR}"

# Stage all changes
git add -A

# Commit with a descriptive message referencing the ticket
git commit -m "<type>(<scope>): <description>

<ticket_key>: <ticket_summary>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

# Push the branch to origin
git push -u origin "${BRANCH_NAME}"
```

**Commit message guidelines**:
- Use conventional commit format: `fix`, `feat`, `refactor`, `chore`, etc.
- Reference the ticket key in the commit body
- Keep the first line under 72 characters

### Step 8: Clean Up Worktree (Optional)

After pushing, inform the user that the worktree can be cleaned up with:

```bash
git worktree remove "${WORKTREE_DIR}"
```

Do NOT automatically remove the worktree - let the user decide.

## Workflow Summary

1. Parse ticket key from arguments
2. Fetch ticket details via Jira MCP
3. Create git worktree from master
4. Implement the fix in the worktree
5. Run quality checks (format, lint, type check)
6. Run related unit tests
7. Commit and push the branch
8. Report completion with branch name and pushed status

## Notes

- All work is done in a separate worktree to avoid disrupting the main working directory
- Branch naming convention: `ADPP-XXXXX-short-description`
- No PR is created - the user can create one manually or use `/pr` when ready
- If the worktree directory already exists, ask the user how to proceed
- Always work from `origin/master` as the base branch
