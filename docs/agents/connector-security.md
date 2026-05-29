---
owner: platform-ops
status: consolidated
---

# Connector Security

Security and governance are central to the SaaS Connector design.

## Credential Management
- **No Raw Tokens in Logs**: Tokens and secrets are never logged. Auditing uses invocation IDs and redacted summaries.
- **Credential References**: Connectors use references to credentials stored in secure vaults.
- **Manual Tokens for Dev**: For development, tokens can be provided via environment variables (e.g., `AGENT_CONNECTOR_GITHUB_TOKEN`).
- **OAuth Integration**: The platform is prepared for OAuth flows, allowing per-tenant and per-user authorization.

## Tenant Boundary
- Every connector action is performed within a `tenant_id` context.
- Credentials and audit logs are isolated by tenant.

## Capability Governance
Connectors declare their capabilities (read, write, comment, etc.). The platform enforces these based on the `AGENT_CONNECTOR_WRITE_ENABLED` flag.

## Audit and Compliance
Every action is audited with:
- Timestamp and Tenant ID
- Connector and Action
- Risk Level
- Dry-run status
- Request/Response summaries (redacted)
