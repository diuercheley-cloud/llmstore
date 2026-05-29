---
owner: platform-ops
status: consolidated
---

# Pilot Activation Playbook

This playbook outlines the steps to activate the Agentic Runtime in Pilot mode.

## Objective
To safely introduce agentic workflows with strict read-only constraints, mandatory approvals, and full observability.

## Prerequisites
- Platform must be up and running.
- Base configurations must be deployed.

## Execution
Run the pilot activation script:
```bash
./scripts/activate-agentic-pilot.sh
```

## State Changes
During execution, the following state changes will occur:
- **Deployment mode:** `DEPLOYMENT_MODE=pilot`
- **Runtime:** `AGENT_RUNTIME_ENABLED=true`
- **Workflows:** `AGENT_STATEFUL_WORKFLOWS_ENABLED=true`
- **Connectors:** `AGENT_CONNECTOR_WRITE_ENABLED=false` with external network governed
- **Approvals:** `AGENT_HUMAN_APPROVAL_ENABLED=true`
- **Budgets:** `AGENT_STRICT_BUDGETS=true`
- **Evaluations:** execution stays opt-in, while promotion gates remain enforced
