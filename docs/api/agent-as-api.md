# Agent-as-API Deployment

Expose approved agents as dedicated API endpoints with SLA, rate limiting, versioning, and signed callbacks.

## Architecture

```
control_plane/app/
  models/agent_deployments.py              # 4 models
  api/agent_deployments.py                 # Admin + Public routers
  services/agent_deployments/
    agent_api_deployment.py                # Deployment lifecycle (CRUD, rollback, keys)
    deployment_router.py                   # Rate limiting + concurrency control
    agent_endpoint_registry.py             # Invoke pipeline (validate -> limit -> execute)
    deployment_sla.py                      # SLA config, monitoring, events
    deployment_usage.py                    # Usage tracking, billing stats
```

## Feature Flag

| Flag | Default | Description |
|------|---------|-------------|
| `AGENT_AS_API_ENABLED` | `false` | Gates all deployment endpoints |

```bash
AGENT_AS_API_ENABLED=true
```

## Models

### AgentApiDeployment
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `tenant_id` | String | Tenant owner |
| `agent_id` | UUID FK | Deployed agent |
| `slug` | String(128) | Unique URL slug (e.g. `my-support-bot`) |
| `name` | String(255) | Display name |
| `status` | String(32) | `active` \| `paused` \| `archived` |
| `version` | String(64) | Semantic version |
| `timeout_seconds` | Integer | Sync invoke timeout (default: 30) |
| `max_concurrency` | Integer | Max parallel invocations (default: 10) |
| `retry_max_attempts` | Integer | Retry count (default: 0) |
| `rate_limit_per_minute` | Integer | Per-minute rate limit (default: 60) |
| `rate_limit_per_day` | Integer | Per-day rate limit (default: 10000) |
| `callback_url` | Text | Webhook URL for async completion |
| `callback_secret` | String | HMAC secret for signed callbacks |
| `billing_tier` | String | `free` \| `basic` \| `pro` \| `enterprise` |

### AgentApiEndpointKey
API key scoped to a deployment. Format: `ak_dep_<random>`.

### AgentApiUsageEvent
Tracks every invocation: mode, status, latency, tokens, cost, client IP.

### AgentApiSlaEvent
Records SLA violations: timeout, rate limit, concurrency, error spikes.

## Admin API

All endpoints require `X-Admin-Token` header.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/admin/agents/{id}/deployments` | Create deployment |
| GET | `/admin/agents/deployments` | List deployments |
| GET | `/admin/agents/deployments/{id}` | Get deployment |
| PATCH | `/admin/agents/deployments/{id}` | Update config |
| POST | `/admin/agents/deployments/{id}/pause` | Pause endpoint |
| POST | `/admin/agents/deployments/{id}/resume` | Resume endpoint |
| POST | `/admin/agents/deployments/{id}/archive` | Archive endpoint |
| POST | `/admin/agents/deployments/{id}/rollback` | Rollback to previous version |
| POST | `/admin/agents/deployments/{id}/keys` | Create API key |
| GET | `/admin/agents/deployments/{id}/usage` | Usage statistics |
| GET | `/admin/agents/deployments/{id}/sla` | SLA health summary |

## Public API

All endpoints require `Authorization: Bearer <endpoint_key>`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/agents/{slug}/invoke` | Async invocation |
| POST | `/api/agents/{slug}/invoke-sync` | Sync invocation (blocks) |
| GET | `/api/agents/{slug}/runs/{run_id}` | Get run status |

### Async Invoke Response
```json
{"run_id": "...", "status": "queued", "deployment_slug": "my-bot"}
```

### Sync Invoke Response
```json
{"run_id": "...", "status": "completed", "total_steps": 3, "total_tokens": 150, "estimated_cost_brl": 0.001}
```

### Signed Callback
When `callback_url` is set, on completion:
```
POST {callback_url}
Headers:
  Content-Type: application/json
  X-Agent-Signature: {hmac-sha256 signature}
Body:
  {"run_id": "...", "status": "completed", "deployment_slug": "...", ...}
```

## Deploy Constraints

- Agent must have status `active` or `approved`
- Slug must be unique, 3-64 chars, lowercase alphanumeric + hyphens
- Default API key created automatically on deployment
- Draft/paused/deprecated agents cannot be deployed

## Rate Limiting

- Per-minute and per-day limits per deployment
- In-memory counters (Redis in production)
- Returns 429 with `retry_after_seconds` on limit

## Concurrency Control

- Max concurrent invocations per deployment
- Returns 503 with `retry_after_seconds` when exceeded
- Slot released on completion or error

## Sync Timeout

- Configurable per deployment (`timeout_seconds`)
- Default 30s, max 300s
- Returns 504 on timeout with partial run info

## Rollback

Rollback to any previous version slug:
```json
POST /admin/agents/deployments/{id}/rollback
{"target_version_slug": "my-bot-v1"}
```

## Usage Tracking

Every invocation is recorded with:
- Mode (sync/async), status, latency
- Tokens used, cost in BRL
- Client IP, endpoint key used
- Input/output text (truncated to 1000 chars)

## Testing

1. Deploy active agent: `POST /admin/agents/{id}/deployments` with valid slug
2. Draft agent rejected: returns 400
3. Invoke creates run: `POST /api/agents/{slug}/invoke`
4. Sync timeout: set low timeout, long-running agent returns 504
5. Rate limit: exceed `rate_limit_per_minute` -> 429
6. Callback signed: verify `X-Agent-Signature` header
7. Rollback: deploy v2, rollback to v1 slug
