---
owner: platform-ops
status: consolidated
---

# Salesforce Connector

## Capabilities
- `search_accounts`: Search for accounts.
- `get_account`: Retrieve account details.
- `create_task`: Create a task associated with an account (requires `AGENT_CONNECTOR_WRITE_ENABLED=true`).

## Required Scopes
- `api`
- `refresh_token`

## Environment Variables
- `AGENT_CONNECTOR_SALESFORCE_TOKEN`: Manual token for development.
