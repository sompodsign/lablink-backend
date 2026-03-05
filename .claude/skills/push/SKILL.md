---
name: push
description: Commit all current git changes and push the current branch to its remote. Use when the user asks to push work, publish local edits, or quickly commit-and-push with an automatically generated commit message and no history rewriting.
---

# Push

## Workflow

1. Verify repository state with `git status --short --branch`.
2. Stage all changes (staged, unstaged, and untracked) with `git add -A`.
3. Confirm staged set with `git diff --cached --name-status`.
4. If nothing is staged, stop and report that there is nothing to commit.
5. Generate a concise imperative commit message from the staged diff summary.
6. Create one commit with the generated message.
7. Push current branch with `git push`.
8. Report commit hash, commit message, and pushed branch.

## Commit Message Generation

- Derive the message from changed files and dominant intent.
- Prefer pattern: `<Verb> <scope> <intent>`.
- Use imperative verbs such as `Fix`, `Update`, `Add`, `Refactor`, `Remove`, `Configure`.
- Keep message short (about 5-10 words).
- If changes span multiple unrelated areas, use a broad message like `Update project configuration and service settings`.

## Guardrails

- Commit exactly current working tree changes at run time.
- Do not amend commits unless explicitly requested.
- Do not run destructive commands (`git reset --hard`, `git checkout --`, force push) unless explicitly requested.
- If push is rejected, report the git error and ask how to proceed.
