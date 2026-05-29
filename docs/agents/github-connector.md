---
owner: platform-ops
status: consolidated
---

# GitHub Connector

The GitHub connector allows agents to interact with GitHub repositories, issues, and comments.

## Capabilities

- `SEARCH`: Search repositories.
- `READ`: Get issue details, list issues.
- `COMMENT`: Create issue comments.
- `CREATE`: Create issues.

## Real Mode Implementation

When enabled, the GitHub connector uses the GitHub REST API v3.

### Actions

- `list_issues`: `GET /repos/{owner}/{repo}/issues`
- `get_issue`: `GET /repos/{owner}/{repo}/issues/{issue_number}`
- `create_issue_comment`: `POST /repos/{owner}/{repo}/issues/{issue_number}/comments`
- `search_repositories`: `GET /search/repositories`

### Credentials

Requires a GitHub Personal Access Token (PAT) passed in the `token` field of the credentials dictionary.
