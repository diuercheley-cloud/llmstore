# Agent Observability in Production

## Overview

The Agent Observability platform provides an end-to-end view of agent executions, including tool calls, policy decisions, cost tracking, and human-in-the-loop approvals. All telemetry is correlated by `run_id`.

## Core Capabilities

- **Run Timeline:** Every agent run records events chronologically. Events include `run.started`, `tool.called`, `memory.read`, `approval.requested`, and `policy.denied`.
- **Cost Tracking:** The platform records LLM prompts and completion tokens, converting them to estimated cost in BRL.
- **Data Sanitization:** Tool outputs and user inputs containing sensitive phrases (`secret`, `key`) are automatically redacted before being logged to timelines or trace exports.
- **Metrics Export:** Prometheus metrics are published for run durations, tool side effects, failures, and approvals.

## Configuration

| Feature Flag | Default | Description |
|---|---|---|
| `AGENT_OBSERVABILITY_ENABLED` | `true` | Enables local tracking of agent runs, metrics, and timelines. |
| `AGENT_TRACE_EXPORT_ENABLED` | `false` | Enables export of OTel traces to external systems. Tenant IDs are hashed for privacy. |

## Endpoints

- **`GET /admin/agents/observability/overview`**: Summary of system health.
- **`GET /admin/agents/runs/{run_id}/timeline`**: Full execution timeline for a run.
- **`GET /admin/agents/runs/{run_id}/cost`**: Detailed cost and token breakdown.
