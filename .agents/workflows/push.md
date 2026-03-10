---
description: Quality check, commit, and push changes to remote for both lablink-backend and lablink-frontend
---

# Push Changes

**IMPORTANT**: Always run this workflow for BOTH repositories:
- `lablink-backend` → `/Users/mdshampadsharkar/Desktop/projects/LabLink/lablink-backend`
- `lablink-frontend` → `/Users/mdshampadsharkar/Desktop/projects/LabLink/lablink-frontend`

For each repository that has uncommitted changes, run the following steps:

### Step 1: Check for Changes
```bash
git -C <repo_path> status --short
```
If no changes, skip this repo and move to the next.

### Step 2: Run Quality Checks
Run the `/quality` workflow inside the repo directory. If quality checks fail after auto-fix: STOP.

### Step 3: Commit Changes
```bash
cd <repo_path>
git add -A
git commit -m "<message>"
```

### Step 4: Push to Remote
```bash
cd <repo_path>
git push -u origin $(git branch --show-current)
```

### Step 5: Report Result
After processing both repos, show push results for each repo that had changes.
