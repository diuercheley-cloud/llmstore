# Mock And Simulation Governance

## Scope

This document defines how `AgentExecutor` may emit non-real outputs.

The goal is strict:

- no silent simulation
- no hidden mock fallback
- no operational success masked as fake execution

## Executor Flags

The executor-specific flags are:

- `AGENT_EXECUTOR_MOCK_MODE`
- `AGENT_EXECUTOR_DRY_RUN_MODE`
- `AGENT_EXECUTOR_ALLOW_SIMULATION`

Default posture:

- `false`
- `false`
- `false`

## Rules

### Mock

Mock execution is allowed only when:

- `AGENT_EXECUTOR_MOCK_MODE=true`

This is a test-only posture.

### Dry Run

Dry-run execution is allowed only when:

- `AGENT_EXECUTOR_DRY_RUN_MODE=true`

Dry-run remains explicit and audit-visible.

### Simulation

Simulation is allowed only when:

- `AGENT_EXECUTOR_ALLOW_SIMULATION=true`

If execution is disabled and this flag is not enabled, the executor fails with an operational error instead of synthesizing a fake result.

## Production And Pilot Posture

In `pilot`, `production`, and `enterprise_managed`:

- non-real executor modes are readiness blockers
- readiness must report the active non-real modes
- GA readiness must fail when non-real executor modes are active in production-capable modes

This means explicit override is visible, auditable, and not GA-safe.

## Required Metadata For Simulated Outputs

Every simulated executor output must carry:

- `execution_mode=mock|simulation|dry_run`
- `simulated=true`
- `reason`
- `policy_decision_id`

Real outputs must carry:

- `execution_mode=real`
- `simulated=false`

## Failure Behavior

When real execution is unavailable and simulation is not explicitly enabled:

- the executor must fail
- the run must not be silently completed
- the failure must be observable in run state and step logs

Examples:

- `Agent execution is disabled. Enable AGENT_EXECUTION_ENABLED=true or AGENT_EXECUTOR_ALLOW_SIMULATION=true.`
- `Mock LLM provider blocked by AgentExecutor. Set AGENT_EXECUTOR_MOCK_MODE=true for explicit test-only use.`

## Readiness Impact

`AgentReadinessService` reports executor posture under:

- `executor_modes`

Possible states:

- `pass`: real execution only
- `warn`: non-real mode active outside production-capable deployment
- `fail`: non-real mode active in `pilot`, `production`, or `enterprise_managed`

## GA Impact

GA readiness fails when:

- mock LLM is active in production-capable mode
- executor mock/dry-run/simulation is active in production-capable mode
- code paths still permit silent or incomplete simulation behavior

## Operational Principle

Mock is a test tool.

Simulation is an explicit override.

Neither may behave like hidden operational success.
