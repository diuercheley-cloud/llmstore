---
owner: platform-ops
status: consolidated
---

# Workflow Webhooks

Stateful workflows can be configured to wait for external HTTP callbacks (webhooks). This allows agents to pause execution until an external event occurs (e.g., an external process completes, or a human provides feedback via a dedicated system).

## Workflow

1. **Subscription**: The workflow (or an admin) registers a webhook wait for a specific `run_id`. This generates a unique `subscription_id` and a `secret_token`.
2. **Waiting State**: The workflow run status can be set to `waiting_webhook` (conceptually), although it typically waits for a signal.
3. **Trigger**: An external system calls the webhook endpoint with the correct `secret_token`.
4. **Signal**: The platform validates the token, records an `AgentWorkflowExternalEvent`, and sends a signal to wake up the workflow.

## Security

- **Secret Tokens**: Every subscription has a unique token that must be provided in the request (usually as a query parameter or header).
- **Redaction**: Incoming payloads are automatically sanitized to redact sensitive keys like `token`, `secret`, or `password` before being stored in the external events log.

## Configuration

- `AGENT_WORKFLOW_WEBHOOKS_ENABLED`: Global toggle for this feature.
