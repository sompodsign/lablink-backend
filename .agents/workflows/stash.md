---
description: Manage git stash operations (save, list, apply, pop, drop, show)
---

# Git Stash Manager

**`/stash`** or **`/stash save`** — Stash current changes:
```bash
branch=$(git branch --show-current) && files=$(git status --short | head -5 | awk '{print $2}' | xargs -I{} basename {} | tr '\n' ', ' | sed 's/,$//') && count=$(git status --short | wc -l | tr -d ' ') && git stash push -u -m "WIP: ${branch} | ${files} (${count} files)"
```

**`/stash list`** — `git stash list`
**`/stash show`** — `git stash show -p stash@{0}`
**`/stash apply`** — `git stash apply stash@{0} && git status --short`
**`/stash pop`** — `git stash pop stash@{0} && git status --short`
**`/stash drop`** — Show contents, confirm, then `git stash drop stash@{0}`

Notes: Use `-u` flag to include untracked files. If index provided (e.g. `apply 2`), use `stash@{2}`.
