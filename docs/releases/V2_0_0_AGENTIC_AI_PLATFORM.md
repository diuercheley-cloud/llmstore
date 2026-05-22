# V2.0.0 Agentic AI Platform

## Summary

`v2.0.0-agentic-ai-platform` closes the runtime loop that was still beta in `v1.10.0-agentic-runtime`:

- Real LLM execution is available through the internal gateway via `AgentLLMProvider`.
- Versioned tool adapters are seeded into the registry and executed through the governed tool pipeline.
- Planner output can execute real tasks through the task engine when explicitly enabled.
- Semantic memory can be retrieved and reinjected into prompt context.
- Worker and queue are documented and deployable as an opt-in profile or Helm deployment.
- `/v1/agents` is the canonical runtime API and `/agents` is retained as a deprecated legacy admin surface.
- Promotion remains blocked when required eval baselines or eval gates fail.

## Required Safe Defaults

- `AGENT_RUNTIME_ENABLED=false`
- `AGENT_REAL_LLM_ENABLED=false`
- `AGENT_LLM_PROVIDER=mock`
- `AGENT_TOOL_ADAPTERS_ENABLED=false`
- `AGENT_TOOL_EXECUTION_ENABLED=false`
- `AGENT_PLANNER_REAL_EXECUTION_ENABLED=false`
- `AGENT_MEMORY_SEMANTIC_SEARCH_ENABLED=false`
- `AGENT_MEMORY_CONTEXT_INJECTION_ENABLED=false`
- `AGENT_WORKER_ENABLED=false`
- `AGENT_ASYNC_EXECUTION_ENABLED=false`
- `AGENT_EVALS_ENABLED=false`
- `AGENT_EVAL_REAL_PROVIDER_ENABLED=false`
- `AGENT_PROMOTION_REQUIRES_EVALS=true`

## Operational Scope

- Canonical tenant runtime API: `/v1/agents`
- Deprecated runtime API: `/agents`
- Real provider path: `AGENT_LLM_PROVIDER=gateway` plus `AGENT_REAL_LLM_ENABLED=true`
- Worker deployment: Docker Compose `agentic` profile or Helm `agentWorker.enabled=true`
- Promotion remains blocked unless eval requirements pass

## Release Gate Expectation

This release is only promotable when test, validation, security, stabilization, operational readiness, complexity, agent eval, and readiness gates succeed and the working tree is clean after the release commit.
