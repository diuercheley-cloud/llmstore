# Agentic Surface: v1.10.0-agentic-runtime

## Classification

- `agentic-runtime`: `beta`
- `agent-registry`: `beta`
- `agent-tool-governance`: `beta`
- `agent-memory`: `beta`
- `agent-planning`: `experimental`
- `agent-hitl`: `beta`
- `agent-observability`: `beta`
- `agent-evals`: `beta`
- `agent-marketplace`: `experimental`
- `agent-admin-ui`: `beta`

## Default Gates

- `AGENT_RUNTIME_ENABLED=false`
- `AGENT_EXECUTION_ENABLED=false`
- `AGENT_TOOL_EXECUTION_ENABLED=false`
- `AGENT_MEMORY_ENABLED=false`
- `AGENT_PLANNING_ENABLED=false`
- `AGENT_HANDOFFS_ENABLED=false`
- `AGENT_MULTI_AGENT_ENABLED=false`
- `AGENT_MARKETPLACE_ENABLED=false`
- `AGENT_HUMAN_APPROVAL_ENABLED=true`
- `AGENT_OBSERVABILITY_ENABLED=true`

## Safety Notes

- No unrestricted autonomy is claimed or enabled.
- Memory remains tenant-scoped and disabled by default.
- Real tools remain disabled by default.
- Destructive tools require explicit enablement and approval.
- Raw prompts are not intended to surface in approvals, replay, observability, or memory views by default.
