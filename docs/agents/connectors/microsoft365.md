---
owner: platform-ops
status: consolidated
---

# Microsoft 365 Connector

## Capabilities
- `search_mail_metadata`: Search for email metadata.
- `get_calendar_events_metadata`: Retrieve calendar event metadata.
- `create_calendar_draft`: Create a draft calendar event (requires `AGENT_CONNECTOR_WRITE_ENABLED=true`).

## Required Scopes
- `Mail.Read`
- `Calendars.ReadWrite`

## Environment Variables
- `AGENT_CONNECTOR_MICROSOFT365_TOKEN`: Manual token for development.
