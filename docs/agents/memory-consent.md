---
owner: platform-ops
status: consolidated
---

# Memory Consent Management

When the system is running with `AGENT_MEMORY_CONSENT_REQUIRED=true`, the platform expects an active consent record from users before saving long-term memories.

## Endpoints
1. `POST /admin/agents/memory/consents`: Register a user's consent for a specific `memory_type` and optionally scoped to an `agent_id`.
2. `GET /admin/agents/memory/consents`: List all consents for a given tenant.

## Process
When `write_memory` is invoked:
1. It validates if consent is required for the specified `memory_type` (long-term memory).
2. It fetches active consent from the database.
3. If no active consent is found, the system rejects the write operation with a `ConsentRequiredError`.

Administrators and the platform itself can revoke a user's consent programmatically, moving its status to `revoked`. No future memory writes will be permitted until consent is granted again.
