---
owner: platform-ops
status: consolidated
---

# Agent Studio

Agent Studio is a low-code visual environment for building, testing, and debugging intelligent agents and multi-agent workflows.

## Features

- **Visual Flow Builder**: Draw agentic DAGs using a drag-and-drop interface.
- **Node-Based Configuration**: Configure agents, tools, memory policies, and human-in-the-loop approvals directly on the canvas.
- **Flow Compiler**: Automatically transform visual flows into executable `AgentPlan` or `AgentWorkflow` objects.
- **Integrated Debugger**: Inspect agent traces, tool calls, and policy decisions in real-time or via replay.

## Surface Status

- `POST /admin/agents/studio/flows`: `beta`
- `GET /admin/agents/studio/flows`: `beta`
- `GET /admin/agents/studio/flows/{id}`: `beta`
- `POST /admin/agents/studio/flows/{id}/validate`: `beta`
- `POST /admin/agents/studio/flows/{id}/compile`: `beta`
- `POST /admin/agents/studio/flows/{id}/explain`: `beta`
- `POST /admin/agents/studio/flows/{id}/dry-run`: `simulated`
- `GET /admin/agents/studio/flows/runs/{run_id}/trace`: `beta`

## Core Concepts

### Nodes
- **Agent**: Represents an LLM reasoning step.
- **Tool Call**: Executes a registered platform tool.
- **Memory**: Read from or write to the agent's persistent memory.
- **Approval**: Defines a human-in-the-loop boundary.
- **Condition**: Implements branching logic based on agent output or tool results.
- **Eval**: Injects an automated evaluation gate into the flow.

### Governance
Agent Studio enforces all platform security rules:
- **Tenant Boundary**: Flows are strictly isolated by tenant.
- **Policy Check**: High-risk tools require explicit approval nodes.
- **Budget Control**: Flow execution is limited by the agent's defined budget.

The dry-run endpoint uses the simulation runtime. It records trace/debug artifacts and blocks side effects, but it does not execute real model calls or external tools.

## Configuration

- `AGENT_STUDIO_ENABLED`: Global toggle for the studio features.
- `AGENT_VISUAL_BUILDER_ENABLED`: Enables the DAG editor.
