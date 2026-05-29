---
owner: platform-ops
status: consolidated
---

# Artifact Versioning, Diff, and Provenance

All changes to artifacts are registered as immutable history versions, facilitating trace history, version comparison, and promotion gates.

## Versioning & Provenance

- **Immutability**: Once written, a version is read-only.
- **Provenance**: Every version tracks creator metadata, including:
  - `creator_type`: `human` or `agent`.
  - `creator_id`: The ID of the editor/agent.
  - `run_id` & `step_id`: If created by an agent, the specific execution run and step details are logged.

## Review & Promotion Gate

Before an artifact status is promoted to `published` (re-deployable baseline state), it must have an approved review:
- **Review**: Humans or peer agents submit approvals or request changes via `POST /admin/agents/artifacts/{id}/review`.
- **Enforcement**: Promotion requests fail unless an approved review matches the current version.

## Export & Content Sanitization

To prevent accidental leak of keys or secrets, the `/admin/agents/artifacts/{id}/export` endpoint filters and sanitizes content:
- Masking of OpenAI/LLM API keys (`sk-...`).
- Redacting JSON/YAML passwords and auth tokens.

## API Endpoints

- **Create Version**
  `POST /admin/agents/artifacts/{id}/versions`

- **Get Diff**
  `GET /admin/agents/artifacts/{id}/diff?from_version=1&to_version=2`

- **Post Review**
  `POST /admin/agents/artifacts/{id}/review`
  Payload:
  ```json
  {
    "version_id": "890259e8-469b-449e-b8d1-93bf28b6d859",
    "reviewer_id": "human-reviewer",
    "reviewer_type": "human",
    "status": "approved",
    "comment": "Looks good"
  }
  ```
