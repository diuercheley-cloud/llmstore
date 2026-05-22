# Agent Registry

The Agent Registry provides a versioned catalog of all agents executing within the system. It governs metadata, permissions, resource boundaries, and compliance properties.

## Architecture

The agent catalog tracks agent definitions and handles automated configuration analysis:

*   **Risk Level Verification**: Every agent has a risk level (`low`, `medium`, `high`, `critical`) defined in `config/agent-registry.yaml`.
*   **Destructive Tools Analysis**: When registering or updating allowed tools, the system automatically checks against `destructive_tools` (e.g. `write`, `delete`, `destroy`, `remove`, `update`). If matched, the system flags the agent with `human_approval_required = True`.
*   **Version Control**: Instruction changes automatically bump the patch version (e.g., `0.1.0` -> `0.1.1`) and snapshot the state into the `agent_versions` table.

## Key Fields

| Field | Type | Description |
| :--- | :--- | :--- |
| `agent_id` | UUID | Unique public identifier for the agent |
| `name` | String | Human-readable name |
| `semantic_version` | String | Current semantic version |
| `owner` | String | Owner identifier (required for activation) |
| `business_purpose` | Text | Business explanation for compliance reviews |
| `supported_surface_status` | String | `supported \| beta \| experimental \| internal` |
| `risk_level` | String | `low \| medium \| high \| critical` |
| `approval_required` | Boolean | Forces promotion approval flow |
| `allowed_tenants` | JSON Array | List of tenant IDs allowed to run this agent |
| `allowed_models` | JSON Array | Approved LLM models for this agent |
| `allowed_tools` | JSON Array | Registered tool permissions |
| `memory_enabled` | Boolean | Toggle long-term memory permissions |
| `human_approval_required` | Boolean | Automatic default gate for destructive actions |
| `eval_baseline` | Text | Performance and alignment baseline evaluation results |
| `instructions` | Text | System prompt and execution instructions |
