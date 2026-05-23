# Multi-Agent Orchestration

The Agentic AI Platform supports advanced multi-agent patterns, allowing multiple specialized agents to collaborate on complex goals.

## Topologies

### Hierarchical

A "Manager" agent coordinates a team of "Specialists".
1. The Manager receives the goal.
2. The Manager breaks the goal into sub-tasks and delegates them to Specialists.
3. Specialists execute their tasks and report back.
4. The Manager synthesizes the final response.

### Debate

Agente collaborate through structured cycles of proposals and critiques.
1. "Proposers" suggest solutions.
2. "Critics" review and provide feedback.
3. Multiple rounds are executed to refine the solution.
4. a "Synthesizer" generates the final answer.

## Governance

- **Delegation Policy**: Controls which agents can delegate tasks to whom based on roles and risk.
- **Loop Guard**: Prevents infinite delegation cycles between agents.
- **Shared Workspace**: Provides a secure, tenant-isolated storage for agents within a team run to share data.

## Configuration Flags

- `AGENT_MULTI_AGENT_ENABLED`: Global toggle for multi-agent features.
- `AGENT_HIERARCHICAL_TEAMS_ENABLED`: Enables hierarchical orchestration.
- `AGENT_DEBATE_TEAMS_ENABLED`: Enables debate-based collaboration.
- `AGENT_SHARED_WORKSPACE_ENABLED`: Enables the shared workspace for agents.
