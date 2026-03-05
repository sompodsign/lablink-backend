# Save Plan to Markdown File

**Command**: `/plan-md-file`

**Purpose**: Write the current plan discussed in this session to `plans/<plan_name>.md`.

## Arguments

- Required: plan name (used as the filename, e.g. `google-ads-importer` → `plans/google-ads-importer.md`)

## Workflow

### Step 1: Determine plan name

If an argument is provided, use it as-is (slugified, lowercase, hyphens) as the filename.
If no argument is provided, derive a short descriptive name from the plan topic discussed in the session.

### Step 2: Ensure `plans/` directory exists

```bash
mkdir -p plans
```

### Step 3: Write the plan file

Synthesise everything planned in this session into a structured markdown file at `plans/<plan_name>.md`.

The file must include:

```markdown
# Plan: <Human-readable title>

## Context
<Why this is being built — problem statement, background>

## Implementation

<The full plan: steps, file changes, code snippets, decisions made>
For each step or file change, include:
- The file path to modify/create
- What changes to make and why

## Verification
<How to verify the implementation is correct — commands to run, things to check>
```

Do NOT truncate or summarise — write the complete plan with enough detail that it can be implemented later from the file alone, without needing the conversation.

## Instructions for Claude Code

1. **Get plan name** — use the argument or derive one from the session
2. **Create `plans/` dir** — run `mkdir -p plans`
3. **Write the file** — synthesise the full plan from this conversation into `plans/<plan_name>.md`
4. **Confirm** — report the file path written

## Exit Behavior

- **SUCCESS**: Plan written to `plans/<plan_name>.md`
- **FAILED**: No plan content found in session to write

## Example Usage

```
/plan-md-file                          # Derives name from session topic
/plan-md-file google-ads-importer      # Saves to plans/google-ads-importer.md
/plan-md-file legacy-tiktok-refactor   # Saves to plans/legacy-tiktok-refactor.md
```
