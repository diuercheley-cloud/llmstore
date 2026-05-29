---
owner: platform-ops
status: consolidated
---

# Agent Observability

Observability for LLM Agents allows operators to monitor, audit, and debug agentic workflows within the platform.

## Features

- **Metrics**: Real-time tracking of agent runs, step latency, tool usage, and costs.
- **Timeline**: Chronological view of all steps and events in an agent run.
- **Tracing**: OpenTelemetry-compatible traces following GenAI semantic conventions.
- **Auditing**: Detailed logs of tool calls and policy decisions.

## Configuration

Agent observability is controlled by the following feature flags:

- `AGENT_OBSERVABILITY_ENABLED`: Set to `true` (default) to enable metrics and timeline tracking.
- `AGENT_TRACE_EXPORT_ENABLED`: Set to `true` to enable external trace export (requires a configured OTel collector). Defaults to `false` for local-only tracing.

## Metrics

The following Prometheus metrics are exported:

| Metric Name | Description | Labels |
|-------------|-------------|--------|
| `llm_agent_runs_total` | Total agent runs started/completed | `agent_id`, `status` |
| `llm_agent_run_failures_total` | Total agent run failures | `agent_id`, `reason` |
| `llm_agent_steps_total` | Total steps executed by agents | `agent_id`, `step_type` |
| `llm_agent_step_latency_seconds` | Latency of agent steps | `agent_id`, `step_type` |
| `llm_agent_tool_calls_total` | Total tool calls | `agent_id`, `tool_name` |
| `llm_agent_tool_failures_total` | Total tool call failures | `agent_id`, `tool_name`, `error_type` |
| `llm_agent_approval_wait_seconds` | Time spent waiting for human approval | `agent_id`, `tool_name` |
| `llm_agent_tokens_total` | Total tokens consumed | `agent_id`, `token_type` |
| `llm_agent_cost_estimated_brl_total` | Estimated cost in BRL | `agent_id` |

## API Endpoints

All endpoints require admin privileges and are prefixed with `/admin/agents/observability`:

- `GET /overview`: High-level summary of agent activity.
- `GET /runs/{run_id}/timeline`: Chronological steps for a specific run.
- `GET /runs/{run_id}/trace`: OTel-compatible trace for a specific run.
- `GET /metrics/summary`: Aggregated metrics for agents.

## Privacy & Security

- **Prompt Masking**: Raw prompts are not logged in the observability timeline by default. Only hashes are stored.
- **Tenant Hashing**: When `AGENT_TRACE_EXPORT_ENABLED` is true, tenant IDs are hashed before export to external collectors.
- **Tool Output Sanitization**: Tool outputs are summarized in logs to avoid exposing sensitive data or inflating log size.
