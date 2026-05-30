# Production SaaS Connectors

This document describes the production-ready features and security posture for SaaS Connectors (GitHub, Jira, Slack, Confluence, Microsoft 365).

## Overview
Connectors can operate in two modes: `mock` (simulated payloads) and `real` (actual HTTP calls). Production environments enforce strict safety interlocks for real mode.

## Feature Flags
- `AGENT_SAAS_CONNECTORS_ENABLED=true`: Globally enables SaaS connectors.
- `AGENT_CONNECTOR_MODE=real`: Set to `real` for actual API calls (defaults to `mock`).
- `AGENT_CONNECTOR_REAL_HTTP_ENABLED=true`: Master gate for any external HTTP traffic.
- `AGENT_CONNECTOR_WRITE_ENABLED=true`: Enables mutating actions (CREATE, UPDATE, DELETE).
- `AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED=true`: Required for non-local network access.
- `AGENT_GITHUB_CONNECTOR_ENABLED=true`: Per-connector enablement.

## Production Safety Features

### 1. Mandatory Human Approval
Actions with `HIGH` or `CRITICAL` risk (typically writes) require explicit operator approval when `AGENT_HUMAN_APPROVAL_ENABLED=true`.

### 2. Write Path Hardening
- **Idempotency**: All writes support idempotency keys to prevent duplicate actions during retries.
- **Receipt Registration**: Every real write operation generates a permanent cryptographic receipt for audit.
- **Write Guard**: Mutation is blocked by default and requires multiple opt-in flags.

### 3. Reliability
- **Retries**: Automatic exponential backoff for 5xx and 429 errors.
- **Rate Limiting**: Enforced per tenant and per provider to protect SaaS quotas.
- **Pagination**: Native support for large result sets via async generators.

### 4. Identity & IAM
- **Credential Reference**: Real mode requires valid credentials (tokens/API keys).
- **Tenant Isolation**: Strictly enforced; connectors cannot access data across tenant boundaries.
- **Agent IAM**: Integration with `CredentialBroker` to ensure agents only use authorized grants.

## Testing
Contract tests use a local fake HTTP server to verify API interactions without external dependencies.
Run tests with:
```bash
PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_connectors_production.py
```
