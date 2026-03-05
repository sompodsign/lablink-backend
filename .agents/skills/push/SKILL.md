---
name: push
description: Commit all current git changes and push the current branch to its remote. Use when the user asks to push work, publish local edits, or quickly commit-and-push with an automatically generated commit message.
---

# Push

## Workflow
1. `git status --short --branch` — verify state
2. `git add -A` — stage all changes
3. `git diff --cached --name-status` — confirm staged set
4. If nothing staged, stop and report
5. Generate concise imperative commit message from diff
6. Create one commit
7. `git push` — push current branch
8. Report commit hash, message, and branch

## Commit Message
- Pattern: `<Verb> <scope> <intent>`
- Verbs: Fix, Update, Add, Refactor, Remove, Configure
- Keep short (5-10 words)

## Guardrails
- No amending unless requested
- No destructive commands unless requested
- If push rejected, report error and ask how to proceed
