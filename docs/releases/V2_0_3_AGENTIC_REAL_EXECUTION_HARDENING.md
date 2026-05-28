# Release v2.0.3 Agentic Real Execution Hardening

## Objective

Close the remaining gaps that prevent production-like autonomous execution from being shipped without caveats.

## Scope

1. `TaskEngine` must not raise `NotImplementedError`-style placeholder failures on real execution paths.
2. `AgentExecutor` must not simulate silently when real execution is disabled or broken.
3. SaaS connectors must expose explicit `mock` or `real` mode behavior.
4. The execution queue must remain durable and the scheduler must remain safe under queue prerequisites.
5. Sandbox escape analysis must be test-covered and real sandbox execution must fail closed without a concrete callable.
6. The Kubernetes operator must reconcile a minimal real surface with explicit `real`/`mock`/`dry_run` mode separation.
7. A real-execution readiness gate must block production-like posture on placeholder or fallback behavior.

## Release Outcomes

- `TaskEngine` output validation now uses the contract class, preventing successful side effects from being retried as operational failures.
- Real tool execution no longer downgrades into implicit simulated output when no implementation is registered.
- Sandbox simulation requires explicit mode. `real` mode without a callable now fails closed.
- Connector real mode now covers the supported real actions without `NotImplementedError` tails, and failed real reads do not fall back into mock payloads.
- Operator reconciliation is explicitly mode-driven and remains idempotent for Deployments, Services, provider secret validation, and status updates.
- The readiness service performs code-aware checks for connector placeholders and implicit tool fallbacks in addition to runtime configuration checks.

## Validation

Primary targeted regression suite for this release:

```bash
PYTHONPATH=control_plane .venv/bin/pytest -q \
  tests/test_agent_executor_governance.py \
  tests/test_saas_connectors_real_mode.py \
  tests/test_agent_queue.py \
  tests/security/test_agent_sandbox_escape.py \
  tests/runtime/test_real_execution_readiness.py \
  tests/kubernetes/test_operator_reconciler.py \
  tests/agent_tasks/test_task_execution.py
```

Expected behavior:

- real execution never emits implicit mock output
- connector real mode errors remain explicit and auditable
- queue lease expiry and DLQ handling remain durable
- sandbox escape cases remain blocked
- production-like readiness blocks on non-real posture

## Operator Notes

- Use `AGENT_CONNECTOR_MODE=real` only with `AGENT_CONNECTOR_REAL_HTTP_ENABLED=true` and connector-specific enablement flags.
- Keep `AGENT_EXECUTOR_MOCK_MODE=false`, `AGENT_EXECUTOR_DRY_RUN_MODE=false`, and `AGENT_EXECUTOR_ALLOW_SIMULATION=false` for production-like operation.
- Use `OPERATOR_MODE=real` for Kubernetes reconciliation with side effects. `mock` and `dry_run` are release-test modes only.
