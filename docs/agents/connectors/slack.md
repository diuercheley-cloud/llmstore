---
owner: platform-ops
status: consolidated
---

# Slack Connector

## Capabilities
- `search_messages`: Search for messages in channels.
- `post_message`: Post a message to a channel (requires `AGENT_CONNECTOR_WRITE_ENABLED=true`).
- `create_thread_reply`: Reply to a message thread (requires `AGENT_CONNECTOR_WRITE_ENABLED=true`).

## Required Scopes
- `chat:write`
- `search:read`
- `channels:history`

## Environment Variables
- `AGENT_CONNECTOR_SLACK_TOKEN`: Manual token for development.
