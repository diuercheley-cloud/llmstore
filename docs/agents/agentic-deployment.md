# Agentic Deployment

## Overview

Agentic deployment refers to running the full Agentic AI Platform with async execution, queue-based job processing, and the agent worker as an official component.

## Modes

### Development Mode (embedded worker)

```bash
AGENT_EMBEDDED_WORKER_ENABLED=true \
AGENT_WORKER_ENABLED=true \
AGENT_EXECUTION_PLANE_ENABLED=true \
AGENT_RUNTIME_ENABLED=true \
make up
```

The worker runs inside the web process. Suitable for local development only.

### Production Mode (separate worker)

```bash
# Start the stack
docker compose --profile agentic up -d

# Or with Helm
helm upgrade --install my-release deploy/helm/llm-inference-stack \
  --set agentWorker.enabled=true \
  --set agentWorker.replicaCount=2
```

The worker runs in its own container/pod, independently scalable.

## Enabling the Full Platform

To enable the full agentic platform, set these environment variables:

```bash
AGENT_RUNTIME_ENABLED=true           # Enable runtime
AGENT_EXECUTION_PLANE_ENABLED=true   # Enable execution plane
AGENT_WORKER_ENABLED=true            # Enable worker
AGENT_ASYNC_EXECUTION_ENABLED=true   # Async job queueing
AGENT_MEMORY_ENABLED=true            # Memory system
AGENT_TOOL_EXECUTION_ENABLED=true    # Tool execution
AGENT_EVALS_ENABLED=true             # Evaluation system
```

## Component Diagram

```
┌─────────────────────────────────────────────────┐
│                  User Request                     │
└────────────────────┬────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────┐
│              control-plane (FastAPI)             │
│  ┌─────────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Agent Runtime│  │  Memory  │  │ Tool Exec  │  │
│  └──────┬──────┘  └──────────┘  └────────────┘  │
│         │                                        │
│         v  (enqueues job)                        │
│  ┌─────────────┐                                 │
│  │ Agent Queue │                                 │
│  └─────────────┘                                 │
└────────────────────┬────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────┐
│              agent-worker (async)                │
│  ┌─────────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Dequeue    │  │  Leases  │  │ Heartbeats │  │
│  └──────┬──────┘  └──────────┘  └────────────┘  │
│         │                                        │
│         v                                        │
│  ┌─────────────────────────────────────────┐    │
│  │        AgentExecutor.execute_step()      │    │
│  │  ┌──────────┐  ┌──────────┐  ┌───────┐  │    │
│  │  │ LLM Call │  │Tool Call │  │Memory │  │    │
│  │  └──────────┘  └──────────┘  └───────┘  │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

## Scaling

### Horizontal Scaling (agent-worker)
- Multiple workers can run concurrently
- Each worker uses `SELECT ... FOR UPDATE SKIP LOCKED` to avoid conflicts
- Leases prevent duplicate execution
- Configure via `replicaCount` in Helm or multiple Docker instances

### Auto-scaling (future)
- HPA based on queue depth (jobs queued / active workers)
- Not yet implemented, but the architecture supports it

## Observability

### Metrics (Prometheus)

| Metric | Type | Description |
|--------|------|-------------|
| `llm_agent_jobs_queued` | Gauge | Jobs waiting in queue (by tenant, agent) |
| `llm_agent_jobs_running` | Gauge | Currently executing jobs |
| `llm_agent_jobs_completed_total` | Counter | Completed jobs |
| `llm_agent_jobs_failed_total` | Counter | Failed jobs |
| `llm_agent_jobs_cancelled_total` | Counter | Cancelled jobs |
| `llm_agent_job_retries_total` | Counter | Retry attempts |
| `llm_agent_dead_letters_total` | Counter | Moved to DLQ |
| `llm_agent_worker_heartbeats_total` | Counter | Worker heartbeats |
| `llm_agent_queue_backpressure_total` | Counter | Backpressure events |

### Logs

```
# Web process
docker compose logs -f control-plane

# Worker process
docker compose logs -f agent-worker

# Both
make logs
```

## Readiness

```bash
# Check readiness
make agentic-readiness

# Inspect queue
make agent-queue-inspect

# Check worker status
make agent-worker-status
```

## Draining

To safely drain the worker before maintenance:

```bash
make agent-worker-drain
```

This cancels all queued jobs. Running jobs are allowed to complete.

## Feature Flag Configuration

All flags default to `false`. Enable only what you need:

```yaml
# feature-flags.yaml
AGENT_RUNTIME_ENABLED: true
AGENT_ASYNC_EXECUTION_ENABLED: true
AGENT_WORKER_ENABLED: true
AGENT_EXECUTION_PLANE_ENABLED: true
AGENT_TOOL_EXECUTION_ENABLED: true
AGENT_MEMORY_ENABLED: true
AGENT_EVALS_ENABLED: true
```
