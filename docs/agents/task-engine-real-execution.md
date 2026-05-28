# TaskEngine Real Execution

## Scope

This document describes the real execution behavior of `control_plane/app/services/agents/task_engine.py`.

The goal is to ensure that a task in real mode will:

- execute via a concrete handler, or
- fail with an explicit operational error

It must never terminate in an incomplete path such as `NotImplementedError("controlled_not_implemented")`.

## Audit Of Legacy Gaps

Legacy `TaskEngine` paths that were removed or replaced:

- `controlled_not_implemented`
  Replaced by explicit operational failures such as `simulation_mode_unsupported` or `unsupported_task_type`.

- implicit mock fallback
  Mock execution only occurs when `AGENT_TASK_MOCK_MODE=true`.

- implicit dry-run fallback
  Dry-run execution only occurs when `AGENT_TASK_DRY_RUN_MODE=true`.

- completed without real execution metadata
  Completed tasks now require `execution_mode`, `receipt_id`, and `output_hash`.

- placeholder tool fallback
  Unregistered tools now fail with `tool_not_registered` unless a real adapter exists.

## Supported Task Types

Real handlers are implemented for:

- `model_reasoning`
- `tool_call`
- `memory_read`
- `memory_write`
- `approval_wait`
- `approval`
- `handoff`
- `workflow_signal`
- `final_response`

Unsupported task types fail with `unsupported_task_type`.

## Execution Contract

Each supported task type validates its input through a versioned contract in:

- `control_plane/app/contracts/agents/task_execution_contract.py`

Current contract version:

- `1.0.0`

## Execution Flow

For every task attempt, `TaskEngine` performs:

1. Load task, plan, run, and agent definition.
2. Resolve execution mode.
3. Create `AgentTaskAttempt`.
4. Create `AgentRunCheckpoint`.
5. Apply policy evaluation.
6. Validate run budget.
7. Execute the handler with timeout.
8. Record `AgentRunStep`.
9. Record `AgentRunReceipt`.
10. Persist `output_hash`.
11. Persist controlled failure metadata when execution fails.

## Execution Modes

### Real

Default mode when neither mock nor dry-run flags are enabled.

### Mock

Enabled only when:

- `AGENT_TASK_MOCK_MODE=true`

### Dry Run

Enabled only when:

- `AGENT_TASK_DRY_RUN_MODE=true`

### Simulation Flag

`AGENT_TASK_SIMULATION_MODE` is not a valid executor.

If set, the engine fails explicitly with:

- `simulation_mode_unsupported`

## Handler Notes

### model_reasoning

- validates `prompt`
- invokes `AgentLLMProvider`
- updates token and cost accounting on the run

### tool_call

- validates `tool_name` and `parameters`
- resolves a real registered tool or adapter-backed tool
- invokes `ToolExecutor`

### memory_read

- validates `memory_type`, `collection_id`, and `limit`
- invokes `AgentMemoryService.read_memory`
- increments memory-read accounting

### memory_write

- validates memory payload
- invokes `AgentMemoryService.write_memory`
- enforces memory policy and consent through the underlying service

### approval_wait

- creates a real approval request
- moves task, plan, and run into waiting state

### handoff

- invokes `AgentHandoffService.initiate_handoff`

### workflow_signal

- invokes `WorkflowSignalManager.send_signal`

### final_response

- marks the run as completed
- persists final `output_hash`

## Failure Model

Examples of controlled failure codes:

- `contract_validation_failed`
- `budget_exceeded`
- `policy_denied`
- `task_timeout`
- `tool_not_registered`
- `unsupported_task_type`
- `simulation_mode_unsupported`
- `operational_error`

Failures generate:

- failed `AgentTaskAttempt`
- failed `AgentRunStep`
- failed `AgentRunReceipt`
- `failure_reason` in task output and attempt error

## Acceptance Guarantees

In real mode:

- no `TaskEngine` path ends with `NotImplementedError`
- no unsupported task is marked completed
- no completed task is persisted without `execution_mode`
- no completed task is persisted without `receipt_id`
- no completed task is persisted without `output_hash`
