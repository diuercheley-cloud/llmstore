# Agentic Runtime Core

The Agentic Runtime Core is a platform consolidated feature adding opt-in execution of LLM-based autonomous agents on top of the existing `llm-inference-stack` core. It enables auditing, step-by-step state checkpointing, and run controls (pause/resume/cancel).

## Feature Flags

All features in the Agentic Runtime are fully opt-in and controlled via environment feature flags:

| Flag | Default | Description |
|---|---|---|
| `AGENT_RUNTIME_ENABLED` | `false` | Global switch for the Agentic Runtime core module. If `false`, endpoints return 400 Bad Request. |
| `AGENT_EXECUTION_ENABLED` | `false` | Controls whether tools are physically executed. If `false`, tools return mock simulations. |
| `AGENT_ASYNC_EXECUTION_ENABLED` | `false` | Enables background async loop execution. If `false`, runs execute synchronously block-by-block. |
| `AGENT_REPLAY_ENABLED` | `true` | Allows read-only replays of past executions using step records/checkpoints. |
| `AGENT_RUNTIME_ADVISORY_MODE` | `true` | Runs in log/warning-only mode without strictly blocking unauthorized executions. |

## Quick Start Configuration

To activate the runtime locally, add the following to your `.env` or environment:

```bash
AGENT_RUNTIME_ENABLED=true
AGENT_EXECUTION_ENABLED=true
AGENT_ASYNC_EXECUTION_ENABLED=true
```

## Admin Management

Administrative operations allow defining agents, versions, allowed tools, and security boundaries.

### Endpoints

- `GET /admin/agents` - List all configured agent definitions.
- `POST /admin/agents` - Create a new Agent profile (starts as `draft`).
- `PATCH /admin/agents/{id}` - Update metadata, policies, allowed tools list, or execution limits.
- `POST /admin/agents/{id}/activate` - Transition definition to `active` status.
- `POST /admin/agents/{id}/deprecate` - Set definition to `deprecated`. Deprecated definitions reject new execution runs.
