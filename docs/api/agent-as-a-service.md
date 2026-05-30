# Agent-as-a-Service (AaaS)

The Agent-as-a-Service layer allows you to consume your specialized agents as reliable external REST services with built-in governance, rate limiting, and async callbacks.

## Invocation Modes

### 1. Asynchronous (Default)
Ideal for long-running agentic tasks. Returns a `run_id` immediately.
- **Endpoint**: `POST /api/v1/agent-service/{agent_id}/invoke`
- **Behavior**: Starts the run and returns. Use the status endpoint or webhooks to get results.

### 2. Synchronous
Ideal for fast reasoning or real-time needs.
- **Endpoint**: `POST /api/v1/agent-service/{agent_id}/invoke-sync`
- **Behavior**: Waits for agent completion (up to a configured timeout, e.g., 30s) and returns the final response directly.

## Service Tiers & Rate Limiting

Usage is governed by tiers to ensure fair resource allocation and predictable costs.

| Tier | Rate Limit (RPM) | Monthly Limit | Features |
|------|------------------|---------------|----------|
| **Free** | 5 | 1,000 | Async only. |
| **Pro** | 50 | 100,000 | Sync mode enabled. |
| **Enterprise** | 500+ | Unlimited | Custom SLAs, high priority. |

## Callback Webhooks

Integrate agent completion into your own backend workflows.
- **Registration**: Register a URL for specific agents.
- **Security**: All callbacks include a `X-Agent-Signature` header (HMAC-SHA256) to verify authenticity using your secret key.

## Usage Tracking & Billing

Every invocation is recorded in the `agent_service_usage` table, tracking:
- Tokens consumed (Prompt/Completion).
- Estimated cost in BRL.
- Execution latency.

These metrics are integrated into the tenant's monthly billing cycle.

## API Examples

### Invoke Agent (Async)
```bash
curl -X POST https://api.llm-stack.com/api/v1/agent-service/{agent_id}/invoke \
  -H "Authorization: Bearer {token}" \
  -d '{"input_text": "Summarize latest market trends"}'
```

### Get Run Status
```bash
curl https://api.llm-stack.com/api/v1/agent-service/runs/{run_id} \
  -H "Authorization: Bearer {token}"
```
