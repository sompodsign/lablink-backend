# Push Command

**Command**: `/push`

**Purpose**: Quality check, commit, and push

**Description**: Runs quality checks with auto-fix, commits all changes, and pushes to remote.

## Arguments

- Optional commit message. If not provided, generates one from changed files.

## Workflow

### Step 1: Run Quality Checks

Run the `/quality` skill to check and auto-fix code quality issues BEFORE committing.

**If quality checks fail after auto-fix**: STOP and report issues. Do not commit or push.

### Step 2: Commit Changes

```bash
# Get branch name and changed files for commit message
branch=$(git branch --show-current)
files=$(git status --short | head -5 | awk '{print $2}' | xargs -I{} basename {} | tr '\n' ', ' | sed 's/,$//')

# Stage and commit (includes any quality fixes)
git add -A
git commit -m "<message>"
```

**Commit Message**:
- If argument provided: use that as commit message
- If no argument: generate from branch name and files (e.g., "WIP: ADPP-12345 | file1.py, file2.py")

### Step 3: Push to Remote

```bash
git push -u origin $(git branch --show-current)
```

## Instructions for Claude Code

1. **Run /quality** - Execute the quality skill for checks and auto-fixes
2. **Commit changes** - Stage all changes (including quality fixes) and commit with appropriate message
3. **Push** - Push to remote with upstream tracking
4. **Report result** - Show push result and any PR links if they exist

**Important:**
- Always use the Co-Authored-By trailer for commits
- If quality checks fail after auto-fix, do NOT commit or push
- Use HEREDOC for commit messages to handle special characters

## Exit Behavior

- **SUCCESS**: Quality passed, changes committed, pushed to remote
- **FAILED**: Quality checks failed after auto-fix, changes not committed or pushed

## Example Usage

```
/push                           # Auto-generate commit message
/push fix: resolve auth timeout # Use provided commit message
```
