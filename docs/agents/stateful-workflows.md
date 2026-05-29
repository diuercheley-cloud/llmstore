---
owner: platform-ops
status: consolidated
---

# Stateful Workflows

Stateful Workflows provide a resilient and persistent way to orchestrate long-running agentic tasks. Unlike the standard `TaskEngine`, stateful workflows can survive worker restarts, sleep for long periods without consuming resources, and wait for external signals or approvals.

## Core Concepts

- **Persistence**: Every state transition is recorded in the database.
- **Resilience**: If a worker fails, the `WorkflowRecoveryService` will pick up stuck runs.
- **Scalability**: Workflows are processed by any available worker using distributed locks.

## Workflow States

- `created`: Workflow run initialized.
- `running`: Currently being processed by a worker.
- `sleeping`: Waiting for a timer to fire.
- `waiting_signal`: Waiting for an external signal.
- `waiting_approval`: Waiting for human intervention.
- `waiting_webhook`: Waiting for an external HTTP callback.
- `completed`: Successfully finished.
- `failed`: Terminated with error.
- `cancelled`: Manually stopped.
- `compensated`: Successfully rolled back after failure.

## Governance

- `AGENT_STATEFUL_WORKFLOWS_ENABLED`: Global toggle.
- `AGENT_WORKFLOW_TIMERS_ENABLED`: Enables/disables timer-based wakeups.
- `AGENT_WORKFLOW_WEBHOOKS_ENABLED`: Enables/disables webhook integration.

## Operational Guide (Production Ready)

### Activate
Ensure `AGENT_STATEFUL_WORKFLOWS_ENABLED=true`.

### Monitor
Check workflow success rate in Grafana dashboard "Agent Workflows".

### Troubleshoot
Use `/admin/agents/workflows/tasks` to inspect stuck workflows.

### Rollback
Disable the feature flag or revert to previous version.
