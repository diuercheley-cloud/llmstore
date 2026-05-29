---
owner: platform-ops
status: consolidated
---

# Agent Memory in Production

To securely deploy Agent Memory in a production environment, several configurations and checks have been introduced to ensure data safety, isolation, and compliance.

## Core Features
1. **Opt-in Storage**: Memory features must be explicitly enabled using feature flags `AGENT_MEMORY_ENABLED`, `AGENT_MEMORY_WRITE_ENABLED`, and `AGENT_LONG_TERM_MEMORY_ENABLED`.
2. **Consent Requirement**: When long-term memory is enabled, `AGENT_MEMORY_CONSENT_REQUIRED=true` (the default) ensures that no memory is written without explicit user consent.
3. **Retention Policies**: A retention policy must exist for any memory write to be successful. You can configure `expire_after_days` for automated lifecycle management.
4. **Tenant Isolation**: Data is scoped by tenant. All read, write, export, and search operations enforce tenant boundaries at the database level.
5. **Redaction**: Personal Identifiable Information (PII) and secrets are redacted from memories prior to storage if the active retention policy has `redaction_enabled` set to true.
6. **Auditing**: All reads and writes to memory are logged using `AgentMemoryAccessEvent` which allows observability over who accessed what.
