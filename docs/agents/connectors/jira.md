---
owner: platform-ops
status: consolidated
---

# Jira Connector

## Capabilities
- `search_issues`: Search for issues using JQL.
- `get_issue`: Retrieve issue details.
- `add_comment`: Add a comment to an issue.
- `create_issue`: Create a new issue (requires `AGENT_CONNECTOR_WRITE_ENABLED=true`).

## Required Scopes
- `read:jira-work`
- `write:jira-work`

## Environment Variables
- `AGENT_CONNECTOR_JIRA_TOKEN`: Manual token for development.
