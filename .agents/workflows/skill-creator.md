---
description: Guide for creating high-quality Antigravity skills. Use when the user wants to create a new agent skill or improve an existing one.
---

# Skill Creator

## What is a Skill?

Skills are reusable packages of knowledge that extend agent capabilities. A skill is a folder containing a `SKILL.md` file with instructions the agent can follow when working on specific tasks. Skills follow a **progressive disclosure** pattern: Discovery → Activation → Execution.

## Where Skills Live

| Location | Scope |
|----------|-------|
| `<workspace>/.agent/skills/<skill-folder>/` | Workspace-specific |
| `~/.gemini/antigravity/skills/<skill-folder>/` | Global (all workspaces) |

## Workflow

### Step 1: Gather Requirements

Ask the user the following questions if not already clear:

1. **What specific task does this skill help with?** (e.g., generating GraphQL boilerplate, reviewing migrations)
2. **When should the agent activate this skill?** (trigger conditions)
3. **Does it need helper scripts, examples, or resources?** (beyond just SKILL.md)
4. **Should it be workspace-specific or global?**
5. **Are there existing skills that do something similar?** (avoid duplication)

### Step 2: Review Existing Skills for Patterns

Before creating, scan existing skills to maintain consistency:

```bash
ls -la .agent/skills/
```

Read 2-3 similar skills to understand the project's conventions. Pay attention to:
- YAML frontmatter format (`name`, `description`)
- Heading structure and section ordering
- Level of detail in instructions
- Whether they include extra resources (scripts, examples)

### Step 3: Design the Skill Structure

#### Folder Layout

```
.agent/skills/<skill-name>/
├── SKILL.md         # Required: Main instructions with YAML frontmatter
├── scripts/         # Optional: Helper scripts the agent can run
├── examples/        # Optional: Reference implementations
└── resources/       # Optional: Templates, schemas, or other assets
```

#### SKILL.md Template

```markdown
---
name: <skill-name>
description: <Clear description of what the skill does and when to use it. Written in third person. Include keywords for discovery.>
---

# <Skill Title> — <Short Role Descriptor>

<One-line persona: "You are an expert at..." or "You are a senior...">

## When to Use This Skill

- Use this when...
- This is helpful for...
- Activate when the user asks about...

## Your Role

- <Responsibility 1>
- <Responsibility 2>
- <Responsibility 3>

## Process

### 1. <First Phase>
- <Action items>

### 2. <Second Phase>
- <Action items>

### 3. <Third Phase>
- <Action items>

## Templates / Patterns

### <Pattern Name>
```<language>
<code template or pattern>
```

## Rules

1. ALWAYS do X
2. NEVER do Y
3. When Z happens, do W

## Output Format

<Define expected output structure if applicable>
```

### Step 4: Apply Best Practices Checklist

Before writing the skill files, verify:

- [ ] **Name is unique and kebab-cased** — The `name` field in frontmatter must be a unique identifier (lowercase, hyphens). Defaults to folder name if not provided.
- [ ] **Description is written in third person** — This is what the agent sees when deciding whether to activate the skill. Example: "Generates unit tests for Python code using pytest conventions" (GOOD) vs "Generate tests" (BAD).
- [ ] **Description includes keywords** — Include relevant terms the agent can match against (e.g., "migration", "GraphQL", "security audit").
- [ ] **Skill is focused on ONE thing** — Each skill should do one thing well. Don't create a "do everything" skill; create separate skills for distinct tasks.
- [ ] **Instructions are specific and actionable** — Include exact file paths, command patterns, and code templates the agent can directly use.
- [ ] **Decision trees are included** — For complex skills, add conditional logic: "If the model has X, do Y. Otherwise, do Z."
- [ ] **Scripts are treated as black boxes** — If including helper scripts, tell the agent to RUN them with specific arguments, not read the source code. This keeps the agent's context focused.
- [ ] **Examples are realistic** — If including example files, use real-world patterns from the project.
- [ ] **Rules section is clear** — Use ALWAYS/NEVER/MUST language for non-negotiable constraints.
- [ ] **File size is reasonable** — SKILL.md should be comprehensive but not overwhelming. Offload large reference material to `resources/`.
- [ ] **No sensitive data** — Never include API keys, passwords, or credentials in skill files.

### Step 5: Write the Skill Files

Create the skill folder and files:

```bash
mkdir -p .agent/skills/<skill-name>
```

Write `SKILL.md` with the designed content. If the skill needs additional resources:

- **Scripts**: Create `.agent/skills/<skill-name>/scripts/<script-name>.sh` (or `.py`)
- **Examples**: Create `.agent/skills/<skill-name>/examples/<example-name>.py`
- **Resources**: Create `.agent/skills/<skill-name>/resources/<resource-name>.md`

### Step 6: Verify the Skill

After creating:

1. Read `SKILL.md` back to confirm structure and content
2. Verify the `name` and `description` frontmatter are set correctly
3. Check that all referenced files (scripts, examples, resources) exist
4. Confirm the skill folder is in the correct location
5. Test that the description is clear enough for agent discovery

## Skill Categories and Examples

### Category: Code Generation
Skills that generate boilerplate or scaffold code.
- `graphql-scaffold`: Generates Strawberry v2 GraphQL types, mutations, queries
- `importer-scaffold`: Generates service importer boilerplate
- `test-generator`: Generates test skeletons for modified code

**Key pattern**: Include code templates in fenced blocks the agent can adapt.

### Category: Code Review / Analysis
Skills that analyze code for issues or patterns.
- `code-reviewer`: Reviews code changes for quality and security
- `n1-detector`: Detects N+1 query issues in Django code
- `migration-safety`: Reviews Django migrations for safety issues

**Key pattern**: Include checklists and severity levels (CRITICAL, HIGH, MEDIUM).

### Category: Planning / Design
Skills that help with design decisions and planning.
- `planner`: Creates detailed implementation plans
- `architect`: Designs system architecture and evaluates trade-offs
- `solution-optimizer`: Evaluates if current implementation is optimal

**Key pattern**: Include structured output templates (plans, ADRs, analysis reports).

### Category: Data / Infrastructure
Skills that interact with external systems.
- `db`: Queries PostgreSQL with schema reference
- `sync-db-schema`: Fetches and updates database schema reference

**Key pattern**: Include reference data files in `resources/` and SQL/command templates.

## Writing Effective Descriptions

The `description` field is the **most critical part** — it determines when the agent activates the skill.

**Good descriptions:**
- "Reviews Django migration files for safety issues before commit. Use when migrations are created, modified, or staged for commit. Catches dangerous patterns like data loss, table locks, and missing reverse operations."
- "Generates Strawberry v2 GraphQL boilerplate (types, inputs, mutations, queries) following ADPP conventions. Use when creating GraphQL endpoints or mutations for the ADPP backend."

**Bad descriptions:**
- "Helps with migrations"
- "GraphQL stuff"
- "Code review tool"

**Tips:**
- Start with an action verb: "Generates...", "Reviews...", "Detects...", "Creates..."
- Include WHEN to use: "Use when...", "Use after..."
- Include WHAT it covers: specific technologies, patterns, or domains

## Anti-Patterns to Avoid

1. **Don't make skills too broad** — "Full-stack developer" is not a good skill. "GraphQL mutation generator" is.
2. **Don't duplicate existing skills** — Check what already exists before creating.
3. **Don't include large data files in SKILL.md** — Use `resources/` for reference data.
4. **Don't write vague instructions** — "Review the code" is bad. "Check for N+1 queries by looking for ORM calls inside loops" is good.
5. **Don't forget the persona** — Start with "You are a/an..." to set the agent's mindset.
6. **Don't omit trigger conditions** — Always specify when the skill should be used.

## Notes

- The agent discovers skills by reading descriptions at conversation start
- Users can explicitly mention a skill by name to force activation
- Skills can reference project-specific paths and conventions
- Complex skills benefit from the `resources/` directory pattern (e.g., schema files, templates)
- Keep SKILL.md focused on instructions; offload reference material to separate files
