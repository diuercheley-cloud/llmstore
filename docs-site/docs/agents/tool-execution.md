<!-- synced_from: docs/agents/tool-execution.md -->

> Source of truth: `docs/agents/tool-execution.md`

---
owner: platform-ops
status: consolidated
---

# Agent Tool Execution

The Agent Tool Execution framework provides a secure, audited, and controlled execution layer for executing tools called by agents.

## Feature Flags

Tool execution is gated behind several feature flags configured in `feature-flags.yaml` and loaded via settings:

- `AGENT_TOOL_EXECUTION_ENABLED` (default: `false`): Enables real execution of agent tools. If `false`, any real tool execution will raise an error, allowing only dry-run simulations.
- `AGENT_TOOL_SANDBOX_ENABLED` (default: `true`): Runs all tool commands in an isolated sandbox env (defaulting to local mock).
- `AGENT_DESTRUCTIVE_TOOLS_ENABLED` (default: `false`): Gated check for tools with `destructive` side effect level or categories like `admin_operation` or `shell_command`.
- `AGENT_TOOL_CREDENTIAL_DELEGATION_ENABLED` (default: `false`): Enables looking up and injecting delegated credentials dynamically.
- `AGENT_TOOL_ROLLBACK_ENABLED` (default: `true`): Automatically executes compensation rollback plans on failed operations.

## Side Effect Levels

All registered tools must declare their `side_effect_level`:

- `none`: Read-only queries with no state modifications.
- `read`: Reads data from external sources/filesystems.
- `write`: Modifies resource state, creating side effects. Requires rollback strategy if supported, and human approval if policy dictates.
- `destructive`: Irreversible state updates. Destructive tools require explicit approval, policy allowance, and are completely blocked unless `AGENT_DESTRUCTIVE_TOOLS_ENABLED` is active.
- `external`: Communicates with external third-party systems.

## Policy & Approval Flow

Before execution, every tool call evaluates the policy engine:

1. **Enablement Check**: Active status verified.
2. **RBAC & Permission Check**: Matching grant rules for the tenant/agent.
3. **Approval Gating**: For `write` or `destructive` tools, human approval is requested. If approved via `AgentApprovalRequest`, execution proceeds. If executed by `admin` or `human` actors, approval requirement is bypassed.

## Quota Enforcement

Every tool execution increments usage metrics:
- Daily quotas are reset automatically on midnight UTC.
- Enforced at tenant, agent, tool, and side-effect levels.
- Exceeding daily quotas raises `QuotaExceededError`.
