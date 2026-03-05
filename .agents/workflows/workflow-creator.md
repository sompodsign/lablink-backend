---
description: Guide for creating high-quality Antigravity workflows. Use when the user wants to create a new workflow or improve an existing one.
---

# Workflow Creator

## What is a Workflow?

Workflows are sequences of steps saved as markdown files that guide the agent through repetitive tasks. They are invoked via `/workflow-name` slash commands and can call other workflows using `Call /workflow-name`.

## Where Workflows Live

| Location | Scope |
|----------|-------|
| `.agent/workflows/` | Workspace-specific |
| `~/.gemini/antigravity/workflows/` | Global (all workspaces) |

## Workflow

### Step 1: Gather Requirements

Ask the user the following questions if not already clear:

1. **What task does this workflow automate?** (e.g., deployment, code review, test run)
2. **What are the steps involved?** (sequential actions the agent should perform)
3. **Are there prerequisite workflows?** (e.g., `/quality` before `/commit`)
4. **Should it be workspace-specific or global?**
5. **Does it need `// turbo` or `// turbo-all` annotations?** (for auto-running safe commands)

### Step 2: Review Existing Workflows for Patterns

Before creating, scan existing workflows to maintain consistency:

```bash
ls -la .agent/workflows/
```

Read 2-3 similar workflows to understand the project's conventions.

### Step 3: Design the Workflow Structure

A well-structured workflow follows this template:

```markdown
---
description: <One-line description of what the workflow does — used for discovery>
---

# <Workflow Title>

## Workflow

### Step 1: <Step Name>

<Clear explanation of what to do>

```bash
# Commands to run (if applicable)
<command>
```

### Step 2: <Step Name>

<Instructions with conditional logic if needed>

### Step N: <Final Step>

<Wrap-up actions>

## Instructions

1. **Step summary** — Brief recap of step order and decision points
2. **Conditional behavior** — What to do if a step fails
3. **Important notes** — Edge cases, gotchas

## Exit Behavior

- **SUCCESS**: Conditions for success
- **FAILED**: Conditions for failure

## Notes

- Additional context, naming conventions, tips
```

### Step 4: Apply Best Practices Checklist

Before writing the workflow file, verify:

- [ ] **Description is clear and specific** — The YAML frontmatter `description` field is the ONLY thing shown in the workflow list. Make it descriptive enough for the agent and user to decide when to invoke it.
- [ ] **Steps are numbered and sequential** — Use `### Step N:` headers.
- [ ] **Commands are in fenced code blocks** — Wrap shell commands in ` ```bash ``` ` blocks.
- [ ] **Placeholders use `<angle_brackets>`** — e.g., `<ticket_key>`, `<branch_name>`.
- [ ] **Conditional logic is explicit** — Clearly state "If X happens, do Y. Otherwise, do Z."
- [ ] **Error handling is defined** — Every workflow should specify what happens on failure.
- [ ] **Exit behavior is documented** — SUCCESS, FAILED, and optionally FIXED states.
- [ ] **Calls to other workflows use `Call /name` or `Run the /name workflow`** — This is how workflow chaining works.
- [ ] **File size is under 12,000 characters** — Hard limit from Antigravity.
- [ ] **No unnecessary verbosity** — Be concise; the agent understands context.
- [ ] **Turbo annotations are considered** — Add `// turbo` above safe-to-auto-run steps, or `// turbo-all` if every step is safe.

### Step 5: Write the Workflow File

Create the file at the appropriate location:

- **Workspace**: `.agent/workflows/<workflow-name>.md`
- **Global**: `~/.gemini/antigravity/workflows/<workflow-name>.md`

**Naming convention**: Use kebab-case for the filename (e.g., `deploy-staging.md` → `/deploy-staging`).

### Step 6: Verify the Workflow

After creating:

1. Read the file back to confirm it looks correct
2. Confirm the description matches the intent
3. Check that all referenced workflows (via `Call /name`) actually exist
4. Ensure the file is under 12,000 characters

## Common Patterns from Existing Workflows

### Pattern: Quality Gate Before Action
```markdown
### Step 1: Run Quality Checks
Run the `/quality` workflow. If quality checks fail after auto-fix, STOP and report issues.
```

### Pattern: Multi-Phase Execution
```markdown
### Phase 1: Initial Checks
<run checks>

### Phase 2: Auto-Fix (if any checks failed)
<apply fixes>

### Phase 3: Re-Check (verify fixes)
<re-run checks>
```

### Pattern: Git Branch Workflow
```markdown
### Step 1: Ensure Clean State
```bash
git fetch origin
git stash
git checkout master
git pull origin master
git checkout -b "<branch-name>"
```
```

### Pattern: Return Value for Chaining
```markdown
## Return Value
When used by other workflows (like `/pr`), this workflow should:
- Return success if all checks pass
- Return failure if any checks fail after auto-fix attempt
```

## Anti-Patterns to Avoid

1. **Don't make workflows too broad** — Each workflow should do ONE thing well. Chain them with `Call /name`.
2. **Don't hardcode values** — Use `<placeholders>` for dynamic values.
3. **Don't skip error handling** — Always define what happens when things fail.
4. **Don't assume context** — Include enough info for the agent to execute without prior knowledge.
5. **Don't exceed 12,000 characters** — Split large workflows into smaller composable ones.

## Notes

- Workflows can reference each other: `/workflow-1` can include `Call /workflow-2`
- The slash command name is derived from the filename (minus `.md`)
- Agent-generated workflows from conversation history are also valid — ask the agent to create one from your current session
