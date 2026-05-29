---
owner: platform-ops
status: consolidated
---

# Hierarchical Agents

Hierarchical orchestration is suitable for tasks that can be naturally decomposed into sub-problems handled by specialists.

## Roles

- **Manager**: The entry point for the task. Responsible for planning and synthesis.
- **Specialist**: An agent with a specific set of tools or knowledge (e.g., a "Security Expert", a "Data Analyst").

## Workflow

1. A request is sent to the team endpoint.
2. The `HierarchicalRuntime` initiates the run.
3. The Manager agent is called to analyze the goal.
4. `AgentTeamDelegation` entries are created for each specialist.
5. Specialists are executed.
6. The Manager aggregates the results.

## Governance

High-risk delegations (detected via `DelegationPolicy`) may trigger a human approval boundary.
