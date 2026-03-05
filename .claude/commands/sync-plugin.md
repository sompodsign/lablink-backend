---
description: Sync all local commands, skills, and agents to the adpp-toolkit plugin in the local marketplace. Run after adding/modifying any skills, commands, or agents.
argument-hint: [optional: "validate" to only check without syncing]
---

You are a plugin synchronization assistant. Your job is to sync the project's local Claude Code configuration into the `adpp-toolkit` plugin at `~/.claude/my-marketplace/plugins/adpp-toolkit/`.

## What to Sync

Source → Destination:

1. **Project commands** (`.claude/commands/*.md`) → `~/.claude/my-marketplace/plugins/adpp-toolkit/commands/`
2. **Project skills** (`.claude/skills/`) → `~/.claude/my-marketplace/plugins/adpp-toolkit/skills/`
3. **Project agents** (`.claude/agents/*.md`) → `~/.claude/my-marketplace/plugins/adpp-toolkit/agents/`
4. **User-level agents** (`~/.claude/agents/*.md`) → `~/.claude/my-marketplace/plugins/adpp-toolkit/agents/`

## Skill-to-Agent Mapping

Each agent should have skills relevant to its role. Use this mapping to determine which skills belong to which agent:

| Agent Category | Relevant Skill Types |
|---|---|
| **Code generators** (importer-scaffold, graphql-scaffold) | `sync-db-schema`, `db`, `test`, `django-command` |
| **Reviewers** (code-reviewer, migration-safety, solution-optimizer) | `review-current-changes`, `changes-analyzer`, `quality`, `test`, `db` |
| **Planners** (architect, planner) | `sync-db-schema`, `db`, `changes-analyzer`, `review`, `plan-md-file` |
| **Test-related** (test-generator) | `test`, `db`, `django-command` |
| **Query analyzers** (n1-detector) | `db`, `django-command` |

## Process

### Step 1: Discover All Skills
List all available skills by scanning:
- `.claude/skills/*/SKILL.md` — project skills (use directory name as skill name)
- `.claude/commands/*.md` — project commands (use filename without .md as skill name)

### Step 2: Detect New/Removed Skills
Compare the discovered skills list against each agent's `skills:` field in frontmatter.
Flag:
- **New skills** not assigned to any agent yet
- **Removed skills** still referenced in agents but no longer exist
- **Agent skill gaps** — skills that match an agent's category but are missing

### Step 3: Update Agent Skills
For each new skill found:
1. Determine which agent category it fits (based on the skill's description/purpose)
2. Ask the user which agents should get the new skill (show a recommendation)
3. Update the `skills:` field in the agent's YAML frontmatter

For removed skills:
1. Remove references from all agent `skills:` fields automatically

### Step 4: Diff Check
Compare source and destination files to show what changed:
- New files (exist in source but not destination)
- Modified files (exist in both but differ)
- Removed files (exist in destination but not source)
- Agent skill changes (added/removed skills)

Show this report to the user.

### Step 5: Sync (unless $ARGUMENTS is "validate")
If the user did NOT pass "validate":
1. Copy all commands: `cp -f .claude/commands/*.md ~/.claude/my-marketplace/plugins/adpp-toolkit/commands/`
2. Copy all skills: `cp -rf .claude/skills/* ~/.claude/my-marketplace/plugins/adpp-toolkit/skills/`
3. Copy project agents: `cp -f .claude/agents/*.md ~/.claude/my-marketplace/plugins/adpp-toolkit/agents/`
4. Copy user agents: `cp -f ~/.claude/agents/*.md ~/.claude/my-marketplace/plugins/adpp-toolkit/agents/`
5. Bump the version in `~/.claude/my-marketplace/plugins/adpp-toolkit/.claude-plugin/plugin.json` (increment patch version)
6. Run: `claude plugin update "adpp-toolkit@my-plugins"`

### Step 6: Report
Show a summary:
```
Plugin Sync Complete
====================
Commands:      X synced
Skills:        X synced
Agents:        X synced (Y skills updated)
New skills:    [list of newly assigned skills]
Removed:       [list of removed skill references]
Version:       X.X.X → X.X.Y
Status:        Updated
```

## Important
- NEVER delete files from the plugin that exist in source — only add/overwrite
- If the marketplace directory doesn't exist, warn the user and stop
- If `plugin.json` is missing, warn and stop
- Always bump the patch version so `claude plugin update` detects changes
- When updating agent skills, preserve the existing YAML frontmatter structure — only modify the `skills:` line
- Ask the user before assigning a new skill to agents — don't auto-assign without confirmation
