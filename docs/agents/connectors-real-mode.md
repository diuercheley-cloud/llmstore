# SaaS Connectors: Real Mode

This document describes the "Real Mode" for SaaS connectors in the Agentic AI Platform.

## Overview

Connectors can operate in two modes:
- **Mock Mode (Default):** Returns simulated payloads. Useful for development and CI.
- **Real Mode:** Makes actual HTTP calls to the SaaS provider's API.

## Configuration

### Global Flags

- `AGENT_CONNECTOR_MODE`: Set to `real` to enable real mode globally. Defaults to `mock`.
- `AGENT_CONNECTOR_REAL_HTTP_ENABLED`: Must be `true` to allow any connector to make real HTTP calls. Defaults to `false`.

### Connector-Specific Flags

Each connector must be explicitly enabled for real mode:
- `AGENT_GITHUB_CONNECTOR_ENABLED=true`
- `AGENT_JIRA_CONNECTOR_ENABLED=true`
- `AGENT_SLACK_CONNECTOR_ENABLED=true`
- `AGENT_CONFLUENCE_CONNECTOR_ENABLED=true`
- `AGENT_SALESFORCE_CONNECTOR_ENABLED=true`
- `AGENT_MICROSOFT365_CONNECTOR_ENABLED=true`

## Security and Governance

1. **Credential Validation:** Real mode requires valid credentials (token, api_key, or username/password).
2. **HTTP Guarding:** Real calls are blocked unless `AGENT_CONNECTOR_REAL_HTTP_ENABLED=true`.
3. **Audit Logging:** Every connector execution (real or mock) is logged to the IAM audit trail.
4. **Log Sanitization:** Sensitive information (tokens, keys) is automatically redacted from logs.
5. **Rate Limiting:** Connectors apply rate limits according to the provider's policy.
6. **Timeouts and Retries:** Robust handling of network issues with exponential backoff.

## Mock Fallback

Mock fallback is never implicit on a real execution path in `v2.0.3`.

- `mock` mode is explicit and responses include `"mock": true`
- `real` mode requires the global HTTP gate and connector-specific enablement
- unsupported real actions raise an explicit unsupported-action error
- failed real requests stay failed and auditable; they do not downgrade into mock payloads
