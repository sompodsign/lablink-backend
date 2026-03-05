# REVIEW.md - Branch Diff Review Command

Custom Claude Code command for focused branch diff reviews with a backend-first mindset.

## Command Definition

**`/review <target-branch>`**
```yaml
---
command: "/review"
category: "Code Review"
purpose: "Assess git diff against a specified branch and report prioritized review findings"
wave-enabled: false
performance-profile: "standard"
---
```

## Usage

- Run after checking out the feature branch you want reviewed.
- Invoke with the branch you want to diff against (defaults to `master` if omitted).
- Provide any relevant context (tickets, requirements) as additional message text.

## Review Protocol

When the command runs, Claude should:

1. Start with the highest-severity issues (bugs, regressions, security gaps).
2. Call out incorrect logic or missing edge-case handling.
3. Flag missing or insufficient tests whenever behaviour changes or risk increases.
4. Note readability or maintainability concerns only when they block understanding or future changes.
5. Ignore style nits unless they obscure a defect.
6. If no issues are found, state that explicitly and highlight any residual risks that cannot be ruled out from the diff alone.

## Evidence Requirements

- Base every observation on something visible in the diff.
- Reference files using `path:line` (for example `src/foo.py:42`).
- Keep each comment concise, prioritized, and actionable.

## Output Expectations

- Lead with findings in descending order of severity.
- Group related observations together when it improves clarity.
- Close with outstanding risks or open questions if applicable.
