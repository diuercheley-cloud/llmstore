---
owner: platform-ops
status: consolidated
---

# Tool Safety and Policy Enforcement

This document covers execution governance, feature flags, permissions matching, dry-runs, and rollbacks.

## Execution Policy Engine

Before executing any tool, the executor calls the policy engine to check permission matching:

1.  **Globally Disabled**: If the tool has `enabled = False`, the execution is denied immediately.
2.  **Experimental Status Restriction**: If the calling agent registry entry has `supported_surface_status == "experimental"`, it is barred from executing tools unless the tool defines `dry_run_supported = True`.
3.  **RBAC Permission Match**: If permissions are configured in `agent_tool_permissions`, the calling agent must match at least one of the rules. A rule can specify permission target filters:
    *   `tenant_id`
    *   `agent_id`
4.  **Approval Lock**: If the tool registry entry is marked `requires_approval = True`, execution blocks and prompts for human approval. A safety review can be registered by an administrator via `add_safety_review`. An approved safety review transitions `requires_approval` to `False`.

## Feature Flags Gating

*   `AGENT_TOOL_EXECUTION_ENABLED`: If set to `False`, all tool executions are blocked, raising a `ValueError`.
*   `AGENT_DESTRUCTIVE_TOOLS_ENABLED`: If set to `False`, any tool with `side_effect_level == "destructive"` or categories `admin_operation` / `shell_command` is blocked.

## Dry-run Execution

If the caller executes with `is_dry_run = True`, the executor:
*   Bypasses the underlying callable execution.
*   Bypasses the feature flags check that gates execution.
*   Bypasses approval gating.
*   Records the invocation in the database with status `"dry_run"`.

## Timeout & Rollback Support

Every tool execution requires a positive `timeout_seconds` value. 
The executor enforces this programmatically using `asyncio.wait_for`.

If execution fails or times out, and the tool registry defines `rollback_supported = True`, the executor runs the provided compensation callback (`rollback_callable`) and logs the invocation status as `"rolled_back"`.
