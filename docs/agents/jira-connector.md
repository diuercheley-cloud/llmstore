# Jira Connector

The Jira connector allows agents to interact with Jira issues and comments.

## Capabilities

- `SEARCH`: Search issues using JQL.
- `READ`: Get issue details.
- `COMMENT`: Add comments to issues.
- `CREATE`: Create issues.

## Real Mode Implementation

Uses the Jira REST API v3.

### Actions

- `search_issues`: `GET /rest/api/3/search`
- `get_issue`: `GET /rest/api/3/issue/{issue_key}`
- `add_comment`: `POST /rest/api/3/issue/{issue_key}/comment`

### Credentials

Requires:
- `base_url`: The URL of your Jira instance (e.g., `https://your-domain.atlassian.net`).
- Authentication (either `token` or `username`/`password`).
