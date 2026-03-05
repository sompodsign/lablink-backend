---
description: Squash all commits on the current branch into a single commit
---

# Squash Branch Commits

### Step 1: Gather Info
```bash
branch=$(git branch --show-current)
merge_base=$(git merge-base HEAD master)
commit_count=$(git rev-list --count $merge_base..HEAD)
```
Safety: STOP if on master/main, 0 commits, or 1 commit.

### Step 2: Show Commits
```bash
git log --oneline $merge_base..HEAD
```

### Step 3: Squash (after user confirmation)
```bash
git reset --soft $merge_base
git commit -m "<message>"
```

### Step 4: Push (if upstream exists)
```bash
git push --force-with-lease origin $(git branch --show-current)
```

NEVER squash on `master`/`main`. Always use `--force-with-lease`.
