<!-- AUTO-GENERATED: do not edit manually -->


# Backup & Restore Capabilities

Overview of platform backup coverage and technical constraints.

## Coverage Matrix

| Scope | Included Components | Excluded Components | Encryption |
| --- | --- | --- | --- |
| logical-agent-backup | agents, workflows, embedding metadata | auth, tenants, billing, audit, policies, persisted config | fernet (encrypted) |

## Technical Constraints

- **Schema Version:** 2.0.0
- **PITR Supported:** ❌
- **Signature Algorithm:** hmac-sha256