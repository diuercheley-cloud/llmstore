# Confluence Connector

## Capabilities
- `search_pages`: Search for pages in spaces.
- `get_page`: Retrieve page content.
- `create_page`: Create a new page (requires `AGENT_CONNECTOR_WRITE_ENABLED=true`).

## Required Scopes
- `read:confluence-content.summary`
- `write:confluence-content`

## Environment Variables
- `AGENT_CONNECTOR_CONFLUENCE_TOKEN`: Manual token for development.
