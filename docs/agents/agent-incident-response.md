# Agent Incident Response

## Overview

The Incident Response feature automatically flags abnormal agent behaviors—such as being stuck, repeated policy denials, or repeated tool failures—so operators can intervene.

## Supported Incident Types

- `run_stuck`: The agent run has exceeded expected execution time without progress.
- `policy_denial_spike`: The agent repeatedly attempts actions violating defined safety policies.
- `repeated_tool_failure`: A specific tool fails repeatedly for the agent.
- `cost_limit_near_breach`: The cost of a single agent run approaches the defined budget limit.

## API Endpoints

- **`GET /admin/agents/incidents`**: List all incidents, filterable by tenant, agent, and status.
- **`GET /admin/agents/incidents/{incident_id}`**: Get full details of an incident.
- **`POST /admin/agents/incidents/{incident_id}/ack`**: Acknowledge an incident (shifts status to `acknowledged`).
- **`POST /admin/agents/incidents/{incident_id}/resolve`**: Resolve an incident with resolution notes.

## Security & RBAC

Incident management endpoints require `admin` roles. Incident payloads automatically redact secrets to prevent operators from inadvertently viewing sensitive context during investigation.