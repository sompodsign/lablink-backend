# Create Pull Request

Create pull requests for the current branch against both staging and the latest release/sprint branch.

## Prerequisites

**MANDATORY**: Before creating PRs, run the `/quality` command to ensure code quality checks pass.

## Instructions

1. **Run quality checks** - Execute `/quality` command first (check -> fix -> re-check)
2. **Find target branches** - Identify staging and the latest `release/sprint<number>` branch
3. **Commit uncommitted changes** - Stage and commit any uncommitted changes
4. **Push to remote** - Ensure all commits are pushed
5. **Analyze changes** - Review commits and diffs since branching from master
6. **Generate PR content** - Create title and description based on ALL changes
7. **Create PRs** - Use GitHub CLI to create both pull requests

### Step 1: Quality Checks (MANDATORY)

Run the `/quality` skill first. If quality checks fail after auto-fix, STOP and report issues.

```
/quality
```

If quality checks pass, continue to Step 2.

### Step 2: Find Target Branches

```bash
# Find the latest release/sprint branch
git fetch origin
git branch -r | grep 'release/sprint' | sort -t't' -k2 -n | tail -1
```

### Step 3: Commit Uncommitted Changes (IMPORTANT)

**ALWAYS check for uncommitted changes and commit them before creating PRs.**

```bash
# Check for uncommitted changes
git status

# If there are changes, stage and commit them
git add -A
git diff --cached --stat  # Review what will be committed

# Commit with appropriate message
git commit -m "$(cat <<'EOF'
<commit message based on changes>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

**Guidelines for committing:**
- Review the changes before committing (use `git diff` or `git diff --cached`)
- Use conventional commit format: `feat:`, `fix:`, `chore:`, `refactor:`, etc.
- Include all modified files unless there's a specific reason to exclude
- If changes are unrelated to the PR, ask user before including

### Step 4: Push to Remote

```bash
# Push branch to origin
git push -u origin $(git branch --show-current)
```

### Step 5: Analyze ALL Changes

```bash
# View ALL commits that will be in the PR (from master)
git log origin/master..HEAD --oneline

# View full diff stats
git diff origin/master...HEAD --stat
```

### Step 4: Create PRs

```bash
# Create PR against staging branch (with [STG] prefix)
command gh pr create --base "staging" --title "[STG] <title>" --body "<body>"

# Create PR against the latest release/sprint branch (with [PROD] prefix)
command gh pr create --base "<release-branch>" --title "[PROD] <title>" --body "<body>"
```

## PR Format

**Title Prefixes**:
- `[STG]` - For PRs targeting staging branch
- `[PROD]` - For PRs targeting release/sprint branch

**Title**: Short, descriptive (under 70 chars), follows conventional commits if applicable
- `[STG] feat: Add new feature description`
- `[PROD] fix: Resolve issue with X`

**Body Template**:
```markdown
## Summary
- Brief bullet points of what changed

## Test plan
- [ ] Unit tests added/updated
- [ ] Manual testing performed
- [ ] Existing tests pass

Generated with Claude Code
```

## Complete Workflow Example

```bash
# Step 1: Run quality checks
# (Claude will run /quality skill here)

# Step 2: Find release branch
git fetch origin
RELEASE_BRANCH=$(git branch -r | grep 'release/sprint' | sort -t't' -k2 -n | tail -1 | xargs)

# Step 3: Check and push
git status
git push -u origin $(git branch --show-current)

# Step 4: Create STG PR
command gh pr create --base "staging" --title "[STG] feat: Add feature" --body "## Summary
- Added feature

## Test plan
- [x] Quality checks pass

Generated with Claude Code"

# Step 5: Create PROD PR
command gh pr create --base "$RELEASE_BRANCH" --title "[PROD] feat: Add feature" --body "## Summary
- Added feature

## Test plan
- [x] Quality checks pass

Generated with Claude Code"
```

## Notes

- Branch naming convention: `ADPP-XXXXX-description`
- **staging branch**: For staging environment deployment
- **release/sprint branch**: For production deployment (e.g., `release/sprint346`)
- Always use `command gh` to bypass any shell aliases
- Quality checks MUST pass before creating PRs
- Use `--base` flag with `gh pr create` to specify target branch
