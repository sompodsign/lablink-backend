# Git Stash Manager

Manage git stash operations: save, list, apply, pop, or drop stashed changes.

## Arguments

$ARGUMENTS - Operation to perform (save, list, apply, pop, drop, show). Defaults to `save` if omitted.

## Instructions

IMPORTANT: Keep operations fast. Use a SINGLE Bash call per operation. Never ask interactive questions.

### Operations

**`/stash` or `/stash save`** - Stash current changes
- Run a single command that gets the branch name, builds a message from changed/untracked files, and stashes everything including untracked files (`-u` flag).
- If nothing to stash, `git stash` will report "No local changes to save" — just relay that.

```bash
branch=$(git branch --show-current) && files=$(git status --short | head -5 | awk '{print $2}' | xargs -I{} basename {} | tr '\n' ', ' | sed 's/,$//') && count=$(git status --short | wc -l | tr -d ' ') && git stash push -u -m "WIP: ${branch} | ${files} (${count} files)"
```

**`/stash list`** - List all stashes
```bash
git stash list
```

**`/stash show`** - Show the diff of the latest stash (or specified index)
```bash
git stash show -p stash@{0}
```

**`/stash apply`** - Apply the latest stash and show status
```bash
git stash apply stash@{0} && git status --short
```

**`/stash pop`** - Apply the latest stash, remove it, and show status
```bash
git stash pop stash@{0} && git status --short
```

**`/stash drop`** - Drop the latest stash (or specified index)
1. Show stash contents first for confirmation
2. Ask user to confirm before dropping
```bash
git stash drop stash@{0}
```

### Notes

- If `$ARGUMENTS` contains a stash index (e.g., `apply 2`), use `stash@{2}` instead of `stash@{0}`
- Always use `-u` flag when saving to include untracked files
- Do NOT run separate status/diff checks before stashing — let git report if nothing to stash
