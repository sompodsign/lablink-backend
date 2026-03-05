# List PR Comments (Humans Only)

Fetch and display all **human** comments from the current branch's **PROD** pull request (targeting the `release/sprint*` branch), filtering out all AI and bot accounts (Gemini, Copilot, etc.).

## Instructions

### Step 1: Get the current branch name

```bash
git branch --show-current
```

### Step 2: Find the PROD PR for the current branch

The PROD PR targets a `release/sprint*` branch. List all PRs for the current branch across all states:

```bash
command gh pr list --head "$(git branch --show-current)" --state all \
  --json number,title,state,baseRefName,url \
  --jq '.[] | select(.baseRefName | startswith("release/sprint"))'
```

If no PROD PR is found, inform the user and stop.

If a specific PR number is provided as `$ARGUMENTS`, skip branch detection and use that PR directly.

### Step 3: Detect owner/repo

```bash
gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"'
```

### Step 4: Fetch all three comment types for the PROD PR

#### a) Review comments (inline code comments)

```bash
command gh api "repos/{owner}/{repo}/pulls/{pr_number}/comments" \
  --paginate \
  --jq '[.[] | select(
    (.user.type != "Bot") and
    (.user.login | test("\\[bot\\]|gemini|copilot|coderabbit|deepsource|sonarcloud|codecov|stale|dependabot|renovate|snyk|gpt|openai|claude|anthropic|linear|github-actions"; "i") | not)
  ) | {
    id,
    user: .user.login,
    body: .body,
    path: .path,
    line: (.line // .original_line),
    created_at,
    in_reply_to_id
  }]'
```

#### b) Review summaries (approve / request changes / comment decisions)

```bash
command gh api "repos/{owner}/{repo}/pulls/{pr_number}/reviews" \
  --paginate \
  --jq '[.[] | select(
    (.user.type != "Bot") and
    (.user.login | test("\\[bot\\]|gemini|copilot|coderabbit|deepsource|sonarcloud|codecov|stale|dependabot|renovate|snyk|gpt|openai|claude|anthropic|linear|github-actions"; "i") | not)
  ) | {
    id,
    user: .user.login,
    state,
    body: .body,
    submitted_at
  }]'
```

#### c) General discussion / issue comments

```bash
command gh api "repos/{owner}/{repo}/issues/{pr_number}/comments" \
  --paginate \
  --jq '[.[] | select(
    (.user.type != "Bot") and
    (.user.login | test("\\[bot\\]|gemini|copilot|coderabbit|deepsource|sonarcloud|codecov|stale|dependabot|renovate|snyk|gpt|openai|claude|anthropic|linear|github-actions"; "i") | not)
  ) | {
    id,
    user: .user.login,
    body: .body,
    created_at
  }]'
```

### Step 5: Present results in a structured format

```
## PR #{number}: {title} ({state})
   Base: {baseRefName}
   URL:  {url}

---

### Inline Code Comments  (human reviewers only)
(Comments left on specific lines of code)

[Grouped by file path, threads nested using in_reply_to_id]

📄 `{path}`
  - **@{user}** on line {line} ({created_at}):
    > {body}
    ↳ **@{reply_user}** ({created_at}):
      > {reply_body}

### Review Decisions  (human reviewers only)
(Approve / Request Changes / Comment)

- **@{user}** [{state}] ({submitted_at}):
  > {body}

### Discussion Comments  (human reviewers only)
(General conversation thread)

- **@{user}** ({created_at}):
  > {body}
```

**Display rules:**
- If a section has zero human comments, print: `No human comments in this section.`
- Group inline review comments by file path.
- Nest reply comments under their parent using `in_reply_to_id`.
- Sort all entries chronologically within each section.
- Prefix the Review Decisions state with an emoji:
  - `APPROVED` → ✅
  - `CHANGES_REQUESTED` → ❌
  - `COMMENTED` → 💬
  - `DISMISSED` → 🚫
- At the end, print a summary line:
  `Total human comments: {n} inline + {m} review decisions + {k} discussion = {total}`

## Notes

- Always use `command gh` to bypass shell aliases.
- Use `--paginate` to fetch all pages.
- Bot detection covers both GitHub's `type: "Bot"` field **and** username pattern matching (case-insensitive) for known AI/automation accounts: Gemini, Copilot, CodeRabbit, DeepSource, SonarCloud, Codecov, Dependabot, Renovate, Snyk, and similar.
- If `$ARGUMENTS` contains a PR number, use that instead of auto-detecting.
- This command only targets the **PROD** PR (base branch starts with `release/sprint`). To view the staging PR, pass the PR number explicitly as an argument.
