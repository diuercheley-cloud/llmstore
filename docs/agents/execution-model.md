# Execution Model

The execution model guarantees that agent steps are deterministic, auditable, and trace-isolated.

## Step Tracking

Every action taken by the executor is logged in the `agent_run_steps` database table:
- **step_type**: Categorized into `model_call`, `tool_call`, `memory_read`, `memory_write`, `approval`, `handoff`, or `final`.
- **input_hash**: SHA-256 hash of the step input payload.
- **output_hash**: SHA-256 hash of the step result.
- **status**: Completion status (`success`, `failed`).
- **latency_ms**: Time elapsed executing the step.
- **policy_result**: Optional security/governance engine decision payload.
- **error**: Stack trace or details if execution failed.

## Execution Constraints

- **Max Steps**: Enforced by the `max_steps` property on `AgentDefinition`. The executor aborts execution if `total_steps` exceeds the limit.
- **Max Runtime**: Enforced by `max_runtime_seconds`. The execution loop checks `started_at` and transitions status to `failed` with "Max runtime seconds exceeded" if the runtime exceeds the limit.
- **Cost Guardrails**: Enforced via token/cost metrics (`max_tokens`, `max_cost_brl`).

## Checkpointing and Tool Control

A critical requirement of the architecture is that **checkpoints are written immediately before and after tool calls**.
1. **Before tool call**: Save snapshot of the runtime memory and context to `agent_run_checkpoints` with status `before_tool_call`.
2. **Execute tool**: Retrieve outputs. If `AGENT_EXECUTION_ENABLED=false`, a mock result is simulated, guaranteeing side effects do not execute.
3. **After tool call**: Save snapshot of runtime memory and output hashes with status `after_tool_call`.

## Prompt Privacy

To protect user confidentiality, **raw prompts are never stored in the step logs/database by default**. Input inputs/outputs are instead tracked via SHA-256 hashes inside the database. Full logs only print hashes unless verbose debug mode is explicitly set, preserving zero-leak defaults.
