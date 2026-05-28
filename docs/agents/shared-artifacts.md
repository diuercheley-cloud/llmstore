# Shared Artifacts & Collaborative Editing

Artifacts are versioned assets created and updated dynamically by humans and agents in a workspace.

## Feature Flags

- `AGENT_SHARED_ARTIFACTS_ENABLED`: Enables the artifacts registry endpoints and capabilities. Defaults to `false`.
- `AGENT_COLLABORATIVE_EDITING_ENABLED`: Enables pessimistic and optimistic lock operations for safe concurrent editing. Defaults to `false`.

## Supported Artifact Types

The following types of artifacts are supported by the registry:
- `markdown_doc`: Structured markdown documents.
- `code_file`: Executable code assets (e.g. Python scripts).
- `json_plan`: Agent execution plans.
- `eval_report`: Evaluation outputs.
- `compliance_evidence`: Compliance attestations.
- `support_bundle`: System diagnostic bundles.
- `workflow_definition`: Agent workflows.
- `prompt_baseline`: System instruction baselines.
- `tool_definition`: Custom tool specifications.

## Locking & Concurrency Control

To prevent race conditions between humans and agents:
- **Pessimistic Locking**: An editor can acquire an exclusive lock (`POST /admin/agents/artifacts/{id}/lock`) with a TTL. Edits by other users or agents will be blocked until the lock is released or expires.
- **Optimistic Locking**: Edit payloads can supply the `expected_version_id`. If the current database state differs, the request fails with a concurrency conflict (`409`).

## API Endpoints

- **Acquire Lock**
  `POST /admin/agents/artifacts/{id}/lock`
  Payload:
  ```json
  {
    "holder_id": "agent-1",
    "holder_type": "agent",
    "expires_in_seconds": 300
  }
  ```

- **Release Lock**
  `POST /admin/agents/artifacts/{id}/unlock?holder_id=agent-1`
