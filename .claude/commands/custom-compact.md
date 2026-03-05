# Compact - Session Handoff

Create a handoff document for the next agent to continue work with fresh context.

## Arguments

$ARGUMENTS - A short title describing the conversation topic (e.g., "gam-cost-importer", "auth-refactor"). If not provided, derive a short kebab-case title from the conversation context.

## Instructions

1. **Create folder** - Ensure `.claude/handoff-files/` folder exists
2. **Analyze current session** - Review the full conversation: what was attempted, what succeeded, what failed, all user decisions and preferences
3. **Write handoff file** - Create `.claude/handoff-files/handoff-<title>.md` with all details needed for continuation

### Handoff Document Structure

Create `.claude/handoff-files/handoff-<title>.md` with:

```markdown
# Task Handoff: <Title>

## Objective
[Clear description of the original goal/task]

## Current Status
[Where things stand right now - percentage complete, blockers, etc.]

## What Was Done
[List of completed work with specific file paths and line numbers]

## What Was Tried But Didn't Work
[Failed approaches, errors encountered, dead ends - and WHY they failed]

## User Decisions & Preferences
[Key decisions the user made during the session that affect future work]

## Remaining Work
[Specific tasks left to complete]

## Key Files
[List of relevant files with brief descriptions of what was created/modified]

## Git Status
[Current branch, uncommitted changes, recent commits from this work]

## Context & Notes
[Any other important context, gotchas, or tips for the next agent]
```

### Workflow

```bash
# Create folder if needed
mkdir -p .claude/handoff-files

# Write handoff-<title>.md with session analysis
```

## Notes

- Be specific about errors and failure reasons
- Include file paths and line numbers where relevant
- Capture all user decisions — these are critical for the next agent
- Include git branch name and status of changes
- The next agent should be able to start immediately from this document alone
- Keep it concise but complete
