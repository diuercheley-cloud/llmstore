# Agent-as-API Deployment

## Overview

The Agent-as-API deployment system allows developers to expose approved AI agents as dedicated, secure, and monitored microservice endpoints. Each deployment features its own configuration for SLA, rate limiting, and callbacks, enabling seamless integration into external applications and workflows.

## Key Features

- **Dedicated Slugs**: Every deployment is accessible via a unique URL slug (e.g., `/api/agents/customer-support-v1/invoke`).
- **Endpoint-Specific API Keys**: Security is managed through API keys scoped strictly to a single deployment.
- **SLA Enforcement**:
  - **Timeouts**: Configure maximum execution time for synchronous calls.
  - **Concurrency**: Limit the number of simultaneous active runs per deployment.
  - **Retry Policies**: Automatic retries for transient failures.
- **Inference Modes**:
  - **Synchronous (`invoke-sync`)**: Blocks until the agent completes or timeout occurs.
  - **Asynchronous (`invoke`)**: Returns immediately with a `run_id` for polling.
- **Webhooks & Callbacks**: Signed POST requests are sent to a configured callback URL upon run completion (success or failure).
- **Versioning & Rollback**: Easily switch a deployment's slug to point to a different agent version or roll back to a previous configuration.
- **Usage & Monitoring**: Detailed event logs and statistics for billing and operational visibility.

## API Lifecycle

### 1. Create a Deployment (Admin)
Only agents with `active` or `approved` status can be deployed.

```bash
POST /admin/agents/{agent_id}/deployments
{
  "slug": "support-bot",
  "name": "Production Support Bot",
  "timeout_seconds": 60,
  "max_concurrency": 5,
  "rate_limit_per_minute": 100,
  "callback_url": "https://hooks.my-app.com/agent-results"
}
```

### 2. Manage API Keys (Admin)
Generate a Bearer token for the endpoint.

```bash
POST /admin/agents/deployments/{deployment_id}/keys?name=mobile-app
```

### 3. Invoke the Agent (Public)

**Synchronous:**
```bash
POST /api/agents/support-bot/invoke-sync
Authorization: Bearer ak_dep_...
{
  "input": "How do I reset my password?"
}
```

**Asynchronous:**
```bash
POST /api/agents/support-bot/invoke
Authorization: Bearer ak_dep_...
{
  "input": "Run a complex audit on project X"
}
```

## Security & Callbacks

When using callbacks, the platform signs the payload using the `callback_secret`. You should verify the `X-Agent-Signature` header (HMAC-SHA256) to ensure the request originated from the platform.

```python
# Signature verification example (Python)
import hmac, hashlib
signature = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
assert signature == request.headers["X-Agent-Signature"]
```

## Feature Flags

- `AGENT_AS_API_ENABLED`: Master switch for the deployment system.
