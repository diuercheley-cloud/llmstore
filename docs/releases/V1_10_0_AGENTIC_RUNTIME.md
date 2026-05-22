# v1.10.0 Agentic Runtime

## Summary

`v1.10.0-agentic-runtime` integrates the Agentic AI Platform into the existing stack without changing the default non-agentic posture. The release introduces Agent Registry, Runtime, Tool Governance, Memory, Planning, Human-in-the-Loop approvals, Observability, Evals, and Admin UI surfaces behind explicit feature gates.

## Safe Defaults

- `AGENT_RUNTIME_ENABLED=false`
- `AGENT_EXECUTION_ENABLED=false`
- `AGENT_ASYNC_EXECUTION_ENABLED=false`
- `AGENT_MEMORY_ENABLED=false`
- `AGENT_LONG_TERM_MEMORY_ENABLED=false`
- `AGENT_TOOL_REGISTRY_ENABLED=false`
- `AGENT_TOOL_EXECUTION_ENABLED=false`
- `AGENT_DESTRUCTIVE_TOOLS_ENABLED=false`
- `AGENT_PLANNING_ENABLED=false`
- `AGENT_PLAN_EXECUTION_ENABLED=false`
- `AGENT_HUMAN_APPROVAL_ENABLED=true`
- `AGENT_OBSERVABILITY_ENABLED=true`
- `AGENT_EVALS_ENABLED=false`
- `AGENT_HANDOFFS_ENABLED=false`
- `AGENT_MULTI_AGENT_ENABLED=false`
- `AGENT_MARKETPLACE_ENABLED=false`

## Guardrails

- No agent executes by default.
- Real tools are disabled by default.
- Memory is disabled by default.
- High-risk actions require human approval by default.
- Raw prompts are not displayed by default.
- Cross-tenant memory is out of scope and blocked by design.
- Destructive tools require explicit enablement and approval.
- Supported surface classifies agentic capabilities as beta or experimental.

## Release Scope

- Agent Registry and lifecycle APIs
- Agent Runtime and client execution APIs
- Tool Governance and approval flows
- Tenant-scoped Memory controls
- Planning and task orchestration controls
- HITL administration
- Observability timelines and metrics
- Evals and baselines
- Admin UI surfaces for operators

## Validation

The release gate for this version must run:

```bash
make test
make validate-quick
make security
make stabilization-check
make operational-readiness
make compliance-check
make platform-freeze-check
make complexity-report
make release-gate TAG=v1.10.0-agentic-runtime
bash scripts/check-secrets.sh --all
scripts/check-alembic-integrity.sh
```
