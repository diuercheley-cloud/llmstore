---
owner: platform-ops
status: consolidated
---

# Agent Promotion Workflow

## Environments

Agents transition through the following standard environments:
1. `draft`: Initial development.
2. `staging`: Integrated testing and early evals.
3. `production`: Live traffic, strict enforcement of all safety gates.

## Promotion Gates

Before an agent can be promoted to `production`, the following must be satisfied:

1. **Evaluation Baseline**: A valid, non-stale evaluation run with a pass rate above the minimum threshold (default 95%).
2. **Security Approval**: A human reviewer (role: `agent_reviewer`) must sign off on the promotion.
3. **Operational Health**: No active critical incidents associated with the agent's current version.

## UI Implementation

The **Agent Promotion** page in the Admin UI visualizes these gates and enables/disables the promotion action based on real-time data from the backend.
