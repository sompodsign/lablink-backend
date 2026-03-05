---
description: Quality check, commit, and push changes to remote
---

# Push Changes

### Step 1: Run Quality Checks
Run the `/quality` workflow. If quality checks fail after auto-fix: STOP.

### Step 2: Commit Changes
```bash
git add -A
git commit -m "<message>"
```

### Step 3: Push to Remote
```bash
git push -u origin $(git branch --show-current)
```

### Step 4: Report Result
Show push result and any PR links if they exist.
