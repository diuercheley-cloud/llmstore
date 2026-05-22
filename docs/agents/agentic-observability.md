# Agentic Observability

## Overview
End-to-end telemetry for agentic runs, correlating steps, tools, memory, and handoffs.

## Core Metrics
- `llm_agent_run_duration_seconds`: E2E run latency.
- `llm_agent_tool_duration_seconds`: Latency per tool call.
- `llm_agent_handoff_count`: Frequency of handoffs between agents.
- `llm_agent_policy_denials_total`: Security policy enforcement tracking.

## Trace Correlation
All spans (runs, steps, tools, memory) are linked via `run_id` and parent span relationships. External handoffs are tracked via `agent_trace_links`.

## Security
- **Prompt Redaction**: Raw prompts are automatically stripped from timeline events and trace exports.
- **Tenant Hashing**: `tenant_id` is hashed in observability logs to prevent data leakage.
