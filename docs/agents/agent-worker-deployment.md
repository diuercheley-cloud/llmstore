---
owner: platform-ops
status: consolidated
---

# Agent Worker Deployment

## Overview

The Agent Worker is a standalone background process that polls the execution queue and runs agent steps. It is deployed as a separate process from the web API (control-plane).

## Architecture

```
control-plane (FastAPI web)
    |
    | enqueues AgentExecutionJob
    v
Postgres (agent_execution_jobs)
    |
    | polled by agent-worker(s)
    v
agent-worker (standalone process)
    ├── Dequeue job (SELECT FOR UPDATE SKIP LOCKED)
    ├── Acquire lease (60s, auto-renewed every 15s)
    ├── Execute AgentExecutor.execute_step() loop
    ├── Record heartbeat every 10s
    ├── Handle retry with exponential backoff
    └── Move to DLQ after max attempts
```

## Docker Compose

The `agent-worker` service is part of the `docker-compose.yml` under the `agentic` profile:

```yaml
docker compose --profile agentic up -d
```

This starts the stack with:
- `control-plane` (web API)
- `agent-worker` (job processor)
- `postgres`, `redis`, data planes

Environment variables (auto-configured):
- `AGENT_EXECUTION_PLANE_ENABLED=true`
- `AGENT_WORKER_ENABLED=true`
- `AGENT_RUNTIME_ENABLED=true`

## Kubernetes (Helm)

Enable the agent worker in `values.yaml`:

```yaml
agentWorker:
  enabled: true
  replicaCount: 2
  runtimeEnabled: true
```

The Helm template creates a `Deployment` named `{release}-agent-worker` that:
- Uses the same image as `control-plane`
- Runs `python -m app.workers.agent_worker`
- Connects to the same Postgres and Redis
- Sets `AGENT_WORKER_ENABLED=true`

## Scripts

| Script | Description |
|--------|-------------|
| `scripts/run-agent-worker.sh` | Starts the agent worker process |
| `scripts/agent-worker-status.sh` | Shows worker heartbeats, queue, readiness |
| `scripts/agent-worker-drain.sh` | Cancels all queued jobs (drain) |
| `scripts/agent-queue-inspect.sh` | Inspects queue depth, DLQ, retries, workers |

## Makefile Targets

```bash
make agent-worker          # Start agent worker process
make agentic-up            # Start stack with agentic profile
make agentic-readiness     # Run readiness checks
make agent-queue-inspect   # Inspect queue
make agent-worker-status   # Show worker status
make agent-worker-drain    # Drain queued jobs
```

## Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_EXECUTION_PLANE_ENABLED` | `false` | Master toggle for execution plane |
| `AGENT_WORKER_ENABLED` | `false` | Worker-specific toggle |
| `AGENT_RUNTIME_ENABLED` | `false` | Agent runtime toggle |
| `AGENT_EMBEDDED_WORKER_ENABLED` | `false` | Run worker inside web process (dev only) |

## Worker Lifecycle

1. **Start**: Worker registers heartbeat, enters polling loop
2. **Poll**: Every 100ms (non-busy) or immediately (after job)
3. **Execute**: Dequeue → acquire lease → run steps → complete
4. **Heartbeat**: Every 10s, updates `agent_worker_heartbeats`
5. **Lease renewal**: Every 15s, extends lease to 60s
6. **Failure**: Exponential backoff → DLQ after max attempts
7. **Shutdown**: Marks worker inactive, cancels leases

## Readiness Checks

The readiness endpoint (`GET /admin/agents/observability/readiness`) validates:
- **active_workers** - pass if > 0 heartbeats within 5 min
- **queue_depth** - pass if < 100 queued jobs
- **stuck_runs** - pass if 0 runs running for > 1 hour
- **orphan_leases** - pass if < 10 expired leases
- **dead_letter_queue** - pass if 0 DLQ entries
- **retry_backlog** - pass if < 10 pending retries
- **critical_incidents** - pass if 0 open critical incidents
