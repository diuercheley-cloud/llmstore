# Task Engine Real Execution

The Agent Platform's Task Engine now strictly enforces real execution paths. By default, tasks that cannot be executed in reality will fail rather than silently falling back to placeholder simulation outputs.

## Motivation

Silent simulation paths mask missing functionality and can lead to tasks being marked as "completed" without actual execution, which is unacceptable for production systems and breaks operational readiness assumptions.

## Configuration Flags

Simulation and Mock modes must be explicitly opted into:

- `AGENT_TASK_SIMULATION_MODE`: General simulation fallback flag (disabled by default). If set to `false`, tasks that try to simulate due to missing implementations will fail with a `NotImplementedError` ("controlled_not_implemented").
- `AGENT_TASK_MOCK_MODE`: When enabled, explicitly marks the execution output as `{"status": "mock", "mock": true}` and bypasses real execution logic.
- `AGENT_TASK_DRY_RUN_MODE`: When enabled, tool execution and external calls are executed in a safe dry-run mode, blocking side effects but traversing the actual code paths.

## Contract for Completed Tasks

Every successfully completed task must provide an output payload with the following fields:

- `execution_mode`: Indicates the mode used (`real`, `mock`, `dry_run`).
- `executor_name`: The entity that executed the task (e.g., `task_engine`, `agent_worker`).
- `output_hash`: SHA-256 hash of the deterministic JSON output payload.
- `receipt_id`: A UUID representing the execution receipt.
- `policy_decision_id`: The ID of the policy engine decision that allowed the execution.