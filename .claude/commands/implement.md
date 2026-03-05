# Implement Plan from Markdown File

**Command**: `/implement`

**Purpose**: Read `plans/<plan_name>.md` and implement everything described in it.

## Arguments

- Required: plan name (filename without `.md`, e.g. `google-ads-importer` → reads `plans/google-ads-importer.md`)

## Workflow

### Step 1: Read the plan file

Read `plans/<plan_name>.md` in full. If the file does not exist, stop and report the error.

### Step 2: Understand the plan

Parse the plan sections:
- **Context** — understand the problem and goals
- **Implementation** — the exact steps, file changes, and code to write
- **Verification** — commands to run at the end to confirm correctness

### Step 3: Implement

Execute every step in the Implementation section in order:
- Create or modify files exactly as described
- Follow all project coding standards (PEP8, type hints, absolute imports, etc.)
- Use TodoWrite to track each implementation step as you go

### Step 4: Verify

Run every command listed in the Verification section of the plan.
If verification fails, fix the issues before reporting done.

### Step 5: Report

Summarise what was implemented and the verification results.

## Instructions for Claude Code

1. **Read plan** — `plans/<plan_name>.md` must exist; fail loudly if not
2. **Plan todos** — use TodoWrite to break the implementation into trackable steps before starting
3. **Implement** — follow the plan exactly; do not skip steps or add unrequested changes
4. **Verify** — run all verification commands from the plan
5. **Report** — list files changed and verification output

## Exit Behavior

- **SUCCESS**: All steps implemented, verification passed
- **FAILED**: Plan file not found, or verification failed after implementation

## Example Usage

```
/implement google-ads-importer
/implement legacy-tiktok-refactor
/implement claude-work-personal-switch
```
