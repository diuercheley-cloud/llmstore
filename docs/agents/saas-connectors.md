---
owner: platform-ops
status: consolidated
---

# SaaS Connectors

The Agentic AI Platform supports governed, enterprise-grade connectors for popular SaaS platforms. These connectors evolve the `tool_adapters` beyond local capabilities, providing a secure way for agents to interact with external services.

## Architecture

Connectors are implemented as `ConnectorAdapter` classes, which provide:
- Strict capability-based access control.
- Integrated governance via feature flags.
- Built-in auditing and rate limiting.
- Support for dry-runs and rollbacks (where applicable).

## Governance

All SaaS connectors respect the following feature flags:
- `AGENT_SAAS_CONNECTORS_ENABLED`: Global toggle for all SaaS connectors.
- `AGENT_CONNECTOR_WRITE_ENABLED`: Controls if `write`, `create`, `update`, and `comment` actions are allowed.
- `AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED`: Controls external network access.
- `AGENT_CONNECTOR_OAUTH_ENABLED`: Controls the availability of OAuth flows.

## Available Connectors

- [GitHub](connectors/github.md)
- [Jira](connectors/jira.md)
- [Slack](connectors/slack.md)
- [Confluence](connectors/confluence.md)
- [Salesforce](connectors/salesforce.md)
- [Microsoft 365](connectors/microsoft365.md)

## Operational Guide (Production Ready)

### Activate
Ensure `AGENT_SAAS_CONNECTORS_ENABLED=true`.

### Monitor
Monitor connector API error rates.

### Troubleshoot
Check connector registry status via `/admin/agents/connectors`.

### Rollback
Disable connectors or individual provider flags.
