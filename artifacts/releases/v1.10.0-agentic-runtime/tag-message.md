# Tag Annotation: v1.10.0-agentic-runtime

`v1.10.0-agentic-runtime` delivers the Agentic AI Platform as a default-safe release.

Included in this release:

- Agent Registry and lifecycle controls
- Agent Runtime and client execution APIs
- Tool Governance and approval flows
- Tenant-scoped Memory controls
- Planning and task orchestration controls
- Human-in-the-Loop approvals
- Observability timelines and metrics
- Evals and baseline controls
- Admin UI surfaces for operators

Default safety posture:

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

Guardrails:

- No agent executes by default
- Real tools remain disabled by default
- Memory remains disabled by default
- High-risk actions require human approval by default
- Raw prompts are not exposed by default
- Cross-tenant memory is blocked by design
- Destructive tools require explicit enablement and approval
- Agentic surface remains `beta` or `experimental` until maturity

Validation:

- `make test` PASS
- `make validate-quick` PASS
- `make security` PASS_WITH_WARNINGS
- `make stabilization-check` PASS
- `make operational-readiness` PASS
- `make compliance-check` PASS
- `make platform-freeze-check` PASS
- `make complexity-report` PASS
- `make release-gate TAG=v1.10.0-agentic-runtime` PASS
- `bash scripts/check-secrets.sh --all` PASS
- `scripts/check-alembic-integrity.sh` PASS
