---
owner: platform-ops
status: consolidated
---

# Agentic Incident Response

## Overview
Automated detection and management of operational failures in agentic runs.

## Surface Status

- `GET /admin/agents/incidents/playbooks`: `beta`
- `POST /admin/agents/incidents/{id}/run-playbook`: `beta`

## Incident Types
- `tool_failure_spike`: Abnormal failure rate in specific tools.
- `handoff_loop`: Agents repeatedly handing off tasks without progress.
- `memory_isolation_violation`: Unauthorized cross-tenant memory access attempts.
- `runaway_agent`: Agent run exceeding cost or step safety limits.

## Operational Workflow
1. **Acknowledge**: Signal investigation has started via `/admin/agents/incidents/{id}/ack`.
2. **Investigate**: Use the correlation view (`/admin/agents/runs/{id}/correlation`) to see detailed step logs.
3. **Resolve**: Run a governed playbook or close the incident with notes on mitigation.

## Playbook Execution Notes

The playbook catalog is a real admin surface. `run-playbook` can execute real containment actions when `dry_run=false` and confirmation is present. Because the catalog and action set are still evolving, the surface remains `beta` rather than `supported`.
