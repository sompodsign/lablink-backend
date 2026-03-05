---
description: Quality check and commit changes to current branch (without push)
---

# Commit Changes

### Step 1: Run Quality Checks
Run the `/quality` workflow to check and auto-fix code quality issues BEFORE committing.
**If quality checks fail after auto-fix**: STOP and report issues. Do not commit.

### Step 2: Commit Changes
```bash
branch=$(git branch --show-current)
files=$(git status --short | head -5 | awk '{print $2}' | xargs -I{} basename {} | tr '\n' ', ' | sed 's/,$//')
git add -A
git commit -m "<message>"
```
- If user provided a message: use that
- If no message: generate from branch name and files

### Step 3: Report Result
Show commit hash and summary of changes.
