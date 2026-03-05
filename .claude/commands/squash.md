# Squash Command

**Command**: `/squash`

**Purpose**: Squash all commits on the current branch into a single commit

**Description**: Identifies all commits on the current branch (since it diverged from the main branch), squashes them into a single commit, and optionally pushes to remote.

## Arguments

- Optional commit message. If not provided, generates one from the branch name and a summary of the squashed commits.

## Workflow

### Step 1: Gather Branch Info

```bash
# Get current branch and main branch
branch=$(git branch --show-current)
main_branch="master"

# Find the merge base (where current branch diverged from main)
merge_base=$(git merge-base HEAD $main_branch)

# Count commits to squash
commit_count=$(git rev-list --count $merge_base..HEAD)
```

**Safety checks:**
- If `commit_count` is 0: STOP — no commits to squash
- If `commit_count` is 1: STOP — only one commit, nothing to squash
- If current branch is `master` or `main`: STOP — never squash on main branch

### Step 2: Show Commits to be Squashed

Display the list of commits that will be squashed so the user can confirm:

```bash
git log --oneline $merge_base..HEAD
```

### Step 3: Squash Commits

Use `git reset` to soft-reset to the merge base, keeping all changes staged:

```bash
git reset --soft $merge_base
```

Then commit all staged changes with the squash message:

```bash
git commit -m "<squash_message>"
```

**Commit Message**:
- If argument provided: use that as commit message
- If no argument: use the first commit message on the branch, or generate from branch name (e.g., "squash: ADPP-12345 | N commits")

### Step 4: Push to Remote (if already tracking)

If the branch has an upstream remote tracking branch, force-push the squashed commit:

```bash
git push --force-with-lease origin $(git branch --show-current)
```

Use `--force-with-lease` (safer than `--force`) to avoid overwriting remote changes made by others.

## Instructions for Claude Code

1. **Gather info** — Get current branch, find merge base with master, count commits
2. **Safety checks** — Abort if on master/main, no commits, or only 1 commit
3. **Show commits** — Display all commits that will be squashed
4. **Ask for confirmation** — Show the commit count and ask the user to confirm before squashing
5. **Squash** — `git reset --soft <merge_base>` then `git commit -m "<message>"`
6. **Force push** — If branch has a remote upstream, run `git push --force-with-lease`
7. **Report result** — Show the new single commit hash and message

**Important:**
- NEVER squash on `master` or `main`
- Always use `--force-with-lease` (not `--force`) when pushing
- Always use the Co-Authored-By trailer in the squash commit
- Use HEREDOC for commit messages to handle special characters
- If there is no remote upstream set, skip the push step and inform the user

## Exit Behavior

- **SUCCESS**: All branch commits squashed into one, pushed if upstream exists
- **ABORTED**: Safety check failed (on main, no commits, single commit)

## Example Usage

```
/squash                                    # Auto-generate squash commit message
/squash feat: ADPP-12345 complete feature  # Use provided commit message
```
