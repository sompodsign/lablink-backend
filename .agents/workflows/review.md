---
description: Assess git diff against a specified branch and report prioritized review findings
---

# Branch Diff Review

Run after checking out the feature branch you want reviewed. Defaults to diffing against `master`.

## Review Protocol

1. Start with highest-severity issues (bugs, regressions, security gaps)
2. Call out incorrect logic or missing edge-case handling
3. Flag missing or insufficient tests
4. Note readability concerns only when they block understanding
5. Ignore style nits unless they obscure a defect

## Evidence Requirements

- Base every observation on something visible in the diff
- Reference files using `path:line`
- Keep each comment concise, prioritized, and actionable

## Output

- Lead with findings in descending order of severity
- Group related observations together
- Close with outstanding risks or open questions
