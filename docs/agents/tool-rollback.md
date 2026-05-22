# Tool Rollback & Compensation

To guarantee execution integrity across complex agent plans, the system records side effects and registers compensation actions to reverse changes when a plan fails.

## Side Effect Registration

When an active tool with side effect level `write` or `destructive` is successfully executed, the framework:
1. Inserts a record into the `agent_tool_side_effects` table containing the resource ID and modification payload.
2. Creates an audit event log.

## Rollback Plans

If the tool declares `rollback_supported=True`, the execution pipeline registers a corresponding compensation action in the `agent_tool_rollback_actions` table:
- **Compensation Action**: Name of the revert function (e.g. `rollback_create_file`).
- **Compensation Payload**: Arguments required to undo the changes (typically resource identifier).
- **Initial Status**: Marked as `"pending"`.

## Reversion Lifecycles

Rollback can be triggered automatically or manually:

### 1. Automatic Rollback (On Failure)
If a tool execution fails and `AGENT_TOOL_ROLLBACK_ENABLED` is active, the system automatically fetches all side effects registered during that invocation.
- It iterates through registered rollback actions in **reverse chronological order** (undoing the most recent mutations first).
- Calls the corresponding compensation hook.
- Marks action as `"success"` or `"failed"` and changes invocation status to `"rolled_back"`.

### 2. Manual Rollback (Operator Triggered)
Operators can manually trigger compensation actions for an invocation via the admin API:
- `POST /admin/agent-tools/invocations/{id}/rollback`
- Resolves all pending compensations for the invocation and executes them sequentially.
