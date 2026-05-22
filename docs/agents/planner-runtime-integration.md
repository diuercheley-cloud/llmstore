# Planner and Runtime Integration

This document describes how the Agentic Planning Engine integrates with the real Agent Runtime for task execution.

## Execution Flow

1.  **Decision**: The LLM determines that a goal requires multi-step planning and returns a `planning` decision type.
2.  **Plan Creation**: The `AgentPlanner` creates an `AgentPlan` with a list of `AgentTask` objects, including their dependencies and `input_data`.
3.  **Governance**: If the plan contains high-risk tasks, it is marked as `requires_approval` and the run pauses.
4.  **Task Execution**: The `TaskEngine` iterates through ready tasks (those with all dependencies completed).
5.  **Runtime Integration**:
    *   `model_reasoning` tasks call the `AgentLLMProvider`.
    *   `tool_call` tasks call the `ToolExecutor`.
    *   `memory_read/write` tasks call the `AgentMemoryService`.
    *   `approval` tasks create an `AgentApprovalRequest`.
6.  **Persistence**: Every task execution is recorded as an `AgentTaskAttempt` with its real input and output.
7.  **Completion**: When all tasks are finished, the `AgentPlan` and `AgentRun` are marked as `completed`.

## Task Types

| Task Type | Backend Service | Description |
| :--- | :--- | :--- |
| `model_reasoning` | `AgentLLMProvider` | Executes logic via LLM. |
| `tool_call` | `ToolExecutor` | Executes a real tool via adapter. |
| `memory_read` | `AgentMemoryService` | Retrieves data from short/long-term memory. |
| `memory_write` | `AgentMemoryService` | Persists data to agent memory. |
| `approval` | `HumanApprovalService`| Requests human intervention. |

## Feature Flags

- `AGENT_PLANNER_REAL_EXECUTION_ENABLED`: Set to `true` to enable real task execution.
- `AGENT_REPLAN_ENABLED`: Allows the agent to generate a new plan if a task fails.
