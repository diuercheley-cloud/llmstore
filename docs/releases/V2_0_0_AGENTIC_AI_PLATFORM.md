# V2.0.0 Agentic AI Platform

## Summary

`v2.0.0-agentic-ai-platform` promotes the agent stack from a control-only beta surface to an operational Agentic AI Platform that can plan, execute, call real tools, retrieve memory, use official workers, and block promotion through eval gates while remaining safe-by-default. This line also integrates five critical layers: governed SaaS connectors, resilient stateful workflows, robust reasoning/acting loops, advanced multi-agent orchestration, and Agent Studio with a visual builder plus debugger.

## Release outcomes

- Real LLM execution is available through the internal gateway when `AGENT_REAL_LLM_ENABLED=true` and `AGENT_LLM_PROVIDER=gateway`.
- Versioned tool adapters are seeded into the registry and executed through the governed tool pipeline.
- Governed SaaS connectors expose dry-run and execution APIs while keeping writes and external network access disabled by default.
- Stateful workflow runs can persist, sleep, and wake on signals, webhooks, or polling without pinning a worker for the full wait interval.
- Reasoning loops can repair malformed JSON/structured output and compress context before retry or fallback.
- Multi-agent orchestration supports hierarchical and debate team topologies behind explicit flags.
- Agent Studio adds flow authoring, validation, compilation, and debugger surfaces for operator workflows.
- Planner output can execute real tasks through the task engine when explicitly enabled.
- Semantic memory can be retrieved and reinjected into prompt context behind dedicated flags.
- Worker and queue are documented and deployable as an official opt-in profile or Kubernetes deployment.
- `/v1/agents` is the canonical runtime API and `/agents` is retained only as a deprecated legacy admin surface.
- Promotion remains blocked when required eval baselines or eval regression gates fail.
- Runtime, tool, and memory payloads are tracked as versioned contracts.

## Eight required criteria

| Criterion | v2.0.0 status | Evidence surface |
|---|---|---|
| 1. Agent plans, executes, uses tools, retrieves memory, and completes real tasks | Ready when explicitly enabled | `agent_runtime`, `task_engine`, `tool_executor`, `agent_memory`, `agents_v1.py` |
| 2. Every execution is auditable end to end | Ready | timelines, run events, approvals, replay, receipts, observability admin APIs |
| 3. Every risky action passes policy and approval when required | Ready | policy engine, risk engine, `AGENT_HUMAN_APPROVAL_ENABLED=true`, approval workflows |
| 4. Worker/queue operate officially | Ready | `app.workers.agent_worker`, `deploy/kubernetes/agent-worker.yaml`, operator scripts |
| 5. Evals block promotion | Ready | promotion gate, eval baselines, regression gates, `AGENT_PROMOTION_REQUIRES_EVALS=true` |
| 6. SLOs, metrics, and playbooks exist | Ready | agent SLO classes, dashboards, readiness checks, playbooks |
| 7. Contracts are versioned for runtime, tools, and memory | Ready | `control_plane/app/contracts/agents/`, contract tests |
| 8. Platform remains safe-by-default | Ready | all execution, memory, worker, eval, multi-agent, and marketplace flags stay off by default |

## Five critical layers

| Layer | Release evidence | Default posture |
|---|---|---|
| Governed SaaS connectors | `agent_connectors_admin.py`, connector registry, dry-run/execute APIs, connector tests | Disabled, no writes, no external network |
| Stateful workflows | workflow engine, scheduler, webhooks, polling, recovery tests | Disabled |
| Reasoning/acting loop | structured output validator, output repair, context compressor, reasoning tests | Disabled |
| Multi-agent orchestration | team registry, hierarchical runtime, debate runtime, trace APIs | Disabled |
| Agent Studio and debugger | studio admin API, flow validator/compiler, debug session models, frontend Studio pages | Disabled |

## Required safe defaults

- `AGENT_RUNTIME_ENABLED=false`
- `AGENT_REAL_LLM_ENABLED=false`
- `AGENT_SAAS_CONNECTORS_ENABLED=false`
- `AGENT_CONNECTOR_WRITE_ENABLED=false`
- `AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED=false`
- `AGENT_STATEFUL_WORKFLOWS_ENABLED=false`
- `AGENT_REASONING_LOOP_ENABLED=false`
- `AGENT_REACT_LOOP_ENABLED=false`
- `AGENT_TOOL_EXECUTION_ENABLED=false`
- `AGENT_MEMORY_ENABLED=false`
- `AGENT_WORKER_ENABLED=false`
- `AGENT_EVALS_ENABLED=false`
- `AGENT_HUMAN_APPROVAL_ENABLED=true`
- `AGENT_MULTI_AGENT_ENABLED=false`
- `AGENT_HIERARCHICAL_TEAMS_ENABLED=false`
- `AGENT_DEBATE_TEAMS_ENABLED=false`
- `AGENT_STUDIO_ENABLED=false`
- `AGENT_VISUAL_BUILDER_ENABLED=false`
- `AGENT_DEBUGGER_ENABLED=false`
- `AGENT_MARKETPLACE_ENABLED=false`

## Operational scope

- Canonical tenant runtime API: `/v1/agents`
- Deprecated runtime API: `/agents`
- Real provider path: `AGENT_LLM_PROVIDER=gateway` plus `AGENT_REAL_LLM_ENABLED=true`
- Governed tool path: `AGENT_TOOL_ADAPTERS_ENABLED=true` plus `AGENT_TOOL_EXECUTION_ENABLED=true`
- Governed connector path: `AGENT_SAAS_CONNECTORS_ENABLED=true`, with `AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED=true` and `AGENT_CONNECTOR_WRITE_ENABLED=true` required for real side effects
- Stateful workflow path: `AGENT_STATEFUL_WORKFLOWS_ENABLED=true` with timers, webhook, and polling sub-flags as needed
- Reasoning loop path: `AGENT_REASONING_LOOP_ENABLED=true` and `AGENT_REACT_LOOP_ENABLED=true` with structured output repair and context compression controls
- Memory reinjection path: `AGENT_MEMORY_ENABLED=true` plus semantic/context flags
- Multi-agent path: `AGENT_MULTI_AGENT_ENABLED=true` with `AGENT_HIERARCHICAL_TEAMS_ENABLED=true` or `AGENT_DEBATE_TEAMS_ENABLED=true`
- Studio path: `AGENT_STUDIO_ENABLED=true` with optional `AGENT_VISUAL_BUILDER_ENABLED=true` and `AGENT_DEBUGGER_ENABLED=true`
- Worker deployment: Docker Compose `agentic` profile or Kubernetes `deploy/kubernetes/agent-worker.yaml`
- Promotion path: eval baseline and promotion gate must pass before production status changes

## Release gate expectation

This release is promotable only when:

- the requested make/script validations pass,
- release artifacts are present under `artifacts/releases/v2.0.0-agentic-ai-platform/`,
- the supported surface and API manifests reflect the canonical agentic runtime,
- the working tree can be clean immediately after the release commit.
