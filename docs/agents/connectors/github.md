---
owner: platform-ops
status: consolidated
---

# GitHub Connector

## Capabilities
- `search_repositories`: Search for repositories.
- `get_issue`: Retrieve issue details.
- `create_issue_comment`: Add a comment to an issue.
- `create_issue`: Create a new issue (requires `AGENT_CONNECTOR_WRITE_ENABLED=true`).

## Required Scopes
- `repo`
- `user`

## Environment Variables
- `AGENT_CONNECTOR_GITHUB_TOKEN`: Manual token for development.
