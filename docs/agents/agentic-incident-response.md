---
owner: platform-ops
status: consolidated
---

# Agentic Incident Response

## Overview
Automated detection and management of operational failures in agentic runs.

## Incident Types
- `tool_failure_spike`: Abnormal failure rate in specific tools.
- `handoff_loop`: Agents repeatedly handing off tasks without progress.
- `memory_isolation_violation`: Unauthorized cross-tenant memory access attempts.
- `runaway_agent`: Agent run exceeding cost or step safety limits.

## Operational Workflow
1. **Acknowledge**: Signal investigation has started via `/admin/agents/incidents/{id}/ack`.
2. **Investigate**: Use the correlation view (`/admin/agents/runs/{id}/correlation`) to see detailed step logs.
3. **Resolve**: Close the incident with notes on mitigation.
