# PR Comments

Fetch and display all comments from the pull request(s) associated with the current branch.

## Instructions

1. **Get the current branch name**

```bash
git branch --show-current
```

2. **Find associated PRs for the current branch**

```bash
# List all PRs (open and closed) for the current branch
command gh pr list --head "$(git branch --show-current)" --state all --json number,title,state,baseRefName,url
```

If no PRs are found, inform the user and stop.

3. **For each PR found, fetch all comments**

There are three types of comments on a GitHub PR. Fetch all three:

### a) Issue/conversation comments (top-level PR comments)

```bash
command gh api repos/{owner}/{repo}/pulls/{pr_number}/comments --paginate --jq '.[] | {id, user: .user.login, body: .body, path: .path, line: .line, created_at: .created_at, in_reply_to_id: .in_reply_to_id}'
```

### b) Review comments (comments left during code reviews)

```bash
command gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --paginate --jq '.[] | {id, user: .user.login, state: .state, body: .body, submitted_at: .submitted_at}'
```

### c) Issue comments (general PR discussion comments)

```bash
command gh api repos/{owner}/{repo}/issues/{pr_number}/comments --paginate --jq '.[] | {id, user: .user.login, body: .body, created_at: .created_at}'
```

4. **Detect the repository owner and name automatically**

```bash
gh repo view --json owner,name --jq '.owner.login + "/" + .name'
```

5. **Present the comments in a structured format**

Organize the output as follows:

### Output Format

For each PR:

```
## PR #{number}: {title} ({state})
   Base: {baseRefName}
   URL: {url}

### Review Comments
(Comments left on specific lines of code during reviews)

- **@{user}** on `{path}:{line}` ({created_at}):
  > {body}

### Review Summaries
(Overall review decisions: approved, changes requested, commented)

- **@{user}** [{state}] ({submitted_at}):
  > {body}

### Discussion Comments
(General conversation on the PR)

- **@{user}** ({created_at}):
  > {body}
```

- Group review comments by file path for readability.
- Thread replies together using `in_reply_to_id` when available.
- Sort all comments chronologically within each section.
- If a section has no comments, note "No comments in this section."
- Highlight unresolved review comments if identifiable.

## Notes

- Always use `command gh` to bypass shell aliases.
- Use `--paginate` to ensure all comments are fetched (not just the first page).
- If the branch has multiple PRs (e.g., one for staging, one for release), show comments for all of them.
- If a specific PR number is provided as argument `$ARGUMENTS`, fetch comments only for that PR instead of auto-detecting from the branch.
