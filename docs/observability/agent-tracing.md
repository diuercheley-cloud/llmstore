# Agent Tracing (OpenTelemetry)

The platform follows OpenTelemetry GenAI semantic conventions for agent tracing.

## Trace Structure

Each agent run is represented as a Trace. The root span represents the entire execution of the agent run.

### Root Span Attributes

| Attribute | Description |
|-----------|-------------|
| `agent.id` | Unique ID of the agent |
| `agent.name` | Human-readable name of the agent |
| `agent.version` | Version of the agent definition |
| `agent.run_id` | Unique ID of the execution run |
| `tenant.id` | ID of the tenant (hashed if exported) |

### Step Spans (Child Spans)

Each step in the agent execution is a child span.

| Attribute | Description |
|-----------|-------------|
| `agent.step_id` | Unique ID of the step |
| `agent.step_type` | Type of step (`model_call`, `tool_call`, `memory_read`, `memory_write`, `approval`, `handoff`, `final`) |
| `agent.step_number` | Sequential number of the step |
| `tool.name` | Name of the tool (if `step_type` is `tool_call`) |
| `error.message` | Error message if the step failed |

## Implementation Details

The traces are currently stored internally in the database as `AgentRunStep` and `AgentRunEvent` records. When queried via the `/admin/agents/observability/runs/{run_id}/trace` API, these records are transformed into a structure compatible with OpenTelemetry Trace JSON format.

### Local vs. Exported Traces

By default, traces remain within the platform's database. If `AGENT_TRACE_EXPORT_ENABLED` is set to `true`, the platform can be configured to export these traces to an external OpenTelemetry collector (e.g., Jaeger, Honeycomb, Datadog).

> **Note**: For privacy reasons, when exporting to external collectors, `tenant_id` and other PII are hashed using SHA-256.
