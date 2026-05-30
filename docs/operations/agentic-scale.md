# Agentic Scaling & Operations

This document describes the architecture and procedures for running the Agentic AI Platform at production scale.

## Distributed Architecture

### 1. Task Queuing
The execution plane supports multiple backends for distributed task queuing:
- **PostgreSQL (Default)**: Uses atomic `SKIP LOCKED` queries for durable, transactional queuing.
- **Redis (Optional)**: Provides high-throughput, low-latency queuing using sorted sets for priority.
  - Enabled via `AGENT_QUEUE_BACKEND=redis`.

### 2. Horizontal Worker Scaling
Agent Workers are stateless and horizontally scalable. They use atomic leases to ensure jobs are processed exactly once.
- **Kubernetes**: Scale the `llmworker` deployment to increase throughput.
- **Graceful Shutdown**: Workers support a `DRAIN` mode (SIGUSR1) to finish current jobs before exiting.

### 3. Distributed Tracing
Full lifecycle observability is powered by OpenTelemetry.
- **Scope**: Spans are recorded for runs, steps, model calls, and tool executions.
- **Context Propagation**: Trace context is maintained across the control-plane and worker pool.
- **Export**: Enable `AGENT_OTEL_TRACING_ENABLED=true` to export traces to an external OTLP collector.

## Kubernetes Operator
The `llm-stack-operator` automates the lifecycle of all platform components:
- `LLMInferenceStack`: Control plane and UI.
- `LLMWorker`: Execution worker pool.
- `LLMModelRuntime`: Local inference nodes.
- `LLMTenant`: Tenant-scoped resource management.

## Load Testing
Verify your cluster's capacity using the included load test suite.

### Running a Scale Test
1. Register a test agent.
2. Run the load test script:
```bash
./scripts/load-test-agentic.sh <AGENT_ID> 1000
```

### Key Metrics
- **Queue Lag**: Latency between enqueuing and worker pickup.
- **P95 Latency**: Total execution time for successful runs.
- **Worker Utilization**: Percentage of worker time spent executing jobs.
- **Tool Failure Rate**: Percentage of tool calls that returned an error.
- **Cost/Run**: Estimated cost per successful execution.
