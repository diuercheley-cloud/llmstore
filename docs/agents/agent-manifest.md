# Agent Manifest (agent.yaml)

The `agent.yaml` file is the primary configuration for an agent.

## Fields

| Field | Type | Description |
| :--- | :--- | :--- |
| `name` | string | Unique identifier for the agent. |
| `version` | string | Semantic version (e.g., 1.0.0). |
| `description` | string | Brief summary of the agent's purpose. |
| `instructions_file` | string | Path to a Markdown file containing agent instructions. |
| `model` | string | The LLM to use (e.g., gpt-4o). |
| `tools` | list | List of tool names the agent is allowed to call. |
| `memory_policy` | object | Config for memory retention and search. |
| `eval_suite` | string | Name of the evaluation suite to run. |
| `risk_level` | string | low, medium, high, critical. |
| `owner` | string | Team or developer name. |
| `environment` | string | dev, staging, production. |
| `supported_surface_status` | string | draft, beta, active. |

## Example

```yaml
name: my-agent
version: 1.0.0
instructions_file: instructions.md
model: gpt-4o
tools:
  - web_search
  - db_query
```
