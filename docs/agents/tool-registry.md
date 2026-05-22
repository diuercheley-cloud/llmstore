# Governed Tool Registry

The Governed Tool Registry is a system designed to catalogue, validate, version, and control the capability of agents to execute tool calls in a secure manner. It integrates with RBAC permission policies, risk management, and audit trailing.

## Feature Flags

*   `AGENT_TOOL_REGISTRY_ENABLED` (default `false`): Gates administrative APIs for registering, configuring, and updating agent tools.
*   `AGENT_TOOL_EXECUTION_ENABLED` (default `false`): Globally toggles whether any agent tool call can perform a real execution.
*   `AGENT_DESTRUCTIVE_TOOLS_ENABLED` (default `false`): Gates tool execution for any tools marked with a `destructive` side-effect level or classified under `admin_operation` or `shell_command` categories.

## Tool Definitions

Each registered tool includes metadata governed by the registry:

*   `id`: Unique identifier (UUID).
*   `name`: Unique tool call name.
*   `version`: Semantically versioned string (e.g. `0.1.0`). Changes to schemas automatically increment patch versioning and create snapshot records in `agent_tool_versions`.
*   `description`: Description of what the tool does.
*   `category`: Category classification of the tool. Must be one of:
    *   `retrieval`
    *   `filesystem_safe`
    *   `database_read`
    *   `database_write`
    *   `admin_operation`
    *   `deployment`
    *   `billing`
    *   `support`
    *   `compliance`
    *   `external_api`
    *   `shell_command`
*   `input_schema_json`: JSON schema defining parameters required for execution.
*   `output_schema_json`: JSON schema defining execution returns.
*   `risk_level`: Low, medium, high, critical.
*   `side_effect_level`: None, read, write, destructive, external.
*   `timeout_seconds`: Positive integer representing the mandatory execution timeout.
*   `retry_policy`: Optional retry strategy configuration.
*   `owner`: Owner identifier.
*   `enabled`: If the tool is globally active.
*   `requires_approval`: If tool execution must block on explicit safety reviews.
*   `dry_run_supported`: True if the tool supports side-effect-free dry runs.
*   `rollback_supported`: True if the tool supports compensation routines when execution fails.
*   `docs_url`: Reference documentation link.
*   `data_boundary`: Required for category `external_api` to declare data exposure boundaries.

## Rules & Invariants

1.  **Mandatory Schemas**: All tools must supply both `input_schema_json` and `output_schema_json`.
2.  **Default Gating for Write/Destructive Side Effects**: Registering or updating tools to side-effect levels `write` or `destructive` automatically sets `requires_approval = True`.
3.  **External Boundary Disclosure**: Category `external_api` tools are rejected unless they provide a non-empty `data_boundary` string.
4.  **Shell command Safeguard**: `shell_command` category tools are disabled by default (`enabled = False`) on registration.
5.  **Audit Trailing**: Invocations register SHA-256 hashes of input and output payloads to protect data privacy. Raw payload logs are masked.
