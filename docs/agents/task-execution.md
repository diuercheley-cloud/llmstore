---
owner: platform-ops
status: consolidated
---

# Task Execution

The `TaskEngine` is responsible for the reliable execution of individual tasks within an `AgentPlan`.

## Task Lifecycle

A task starts in the `pending` status.

1.  **Ready Check**: The engine identifies tasks where all parent dependencies are `completed` or `skipped`.
2.  **Running**: Status changes to `running`. An `AgentTaskAttempt` is created to track the start time and input data.
3.  **Execution**: The engine calls the appropriate service based on `task_type`.
4.  **Completion/Failure**:
    *   **Success**: Status changes to `completed`. `output_data` is saved.
    *   **Failure**: Status changes to `failed`. Error is logged. Compensation or retry logic may be triggered.
5.  **Audit**: Every state change and attempt is logged for auditability and debugging.

## Retries and Rollbacks

- **Retries**: If a task fails and `AGENT_AUTO_RETRY_ENABLED` is true, the engine will reset the status to `pending` if `attempt_count < max_attempts`.
- **Compensation**: If a task fails and has a `compensation_action_id`, the `CompensationService` is triggered to revert side effects.

## Task Dependencies

Dependencies are managed via the `agent_task_dependencies` table. A task will NOT be executed until all its dependencies are in a terminal successful state (`completed` or `skipped`).
