# Queue Backpressure & Multi-Tenant Isolation

To prevent resource exhaustion, noisy neighbor problems, and system degradation, the Agent Execution Plane implements a multi-tier backpressure system and strict multi-tenant isolation.

## Concurrency Limits

The backpressure engine evaluates incoming jobs against four distinct tiers of limits:

| Tier | Limit Type | Max Concurrency / Depth | Description |
|---|---|---|---|
| **Global** | Global Queue Depth | 100 active jobs | The maximum total number of active jobs (`queued`, `leased`, `running`, `waiting_approval`) in the entire system. |
| **Tenant** | Tenant Concurrency | 10 active jobs | The maximum concurrent active jobs allowed per tenant. |
| **Agent** | Agent Concurrency | 5 active jobs | The maximum concurrent active jobs allowed for a single `agent_id`. |
| **Risk Level** | Risk Limit | Low: 50<br/>Medium: 10<br/>High: 3<br/>Critical: 1 | Concurrency limit applied globally across all jobs running under a specific agent risk level. |

If any threshold is exceeded, the enqueue request is rejected with a `BackpressureError` and the run is not enqueued.

## Multi-Tenant Isolation Boundaries

The Agent Execution Plane enforces strict data isolation boundaries between tenants:
- All database queries for queue management, leasing, heartbeats, and DLQ filter by `tenant_id`.
- Workers verify tenant ownership before executing any leased job.
- Admin execution APIs (e.g. canceling or retrying a job) require verification of the tenant boundary. For multi-tenant operations, the client must supply the appropriate tenant ID (via headers or context), and access to a job of another tenant is rejected with a `PermissionError` (returning `403 Forbidden` at the HTTP layer).

## Observability & Prometheus Metrics

The execution plane exposes standard Prometheus metrics to monitor queue size, worker state, retries, and backpressure events:

- `llm_agent_jobs_queued`: Current count of jobs in `queued` state.
- `llm_agent_jobs_running`: Current count of jobs in `leased`, `running`, or `waiting_approval` state.
- `llm_agent_jobs_completed_total`: Cumulative counter of successfully completed runs.
- `llm_agent_jobs_failed_total`: Cumulative counter of failed runs.
- `llm_agent_jobs_cancelled_total`: Cumulative counter of cancelled runs.
- `llm_agent_job_retries_total`: Cumulative counter of job retries due to failure/lease expiration.
- `llm_agent_dead_letters_total`: Cumulative counter of jobs moved to the DLQ.
- `llm_agent_worker_heartbeats_total`: Cumulative counter of worker heartbeat signals.
- `llm_agent_queue_backpressure_total`: Cumulative counter of rejected enqueues, labeled by `tenant_id`, `agent_id`, and `limit_type` (e.g., `tenant`, `agent`, `global`, `risk_level_critical`).
