# Naming & API Consistency

## Standardized Terminology
The following terms are standardized across the platform to ensure clarity and consistency:

| Term | Description | Applied In |
|------|-------------|------------|
| `immutable_hash` | Hash representing immutable state (receipts, timelines). | `app.models.governance` |
| `payload_hash` | Hash of the raw request/response content. | `app.models.inference` |
| `replay_safe` | Boolean indicating deterministic execution possibility. | `app.services.reproducibility` |
| `replay_verifiable` | Indicates if a timeline can be verified via replay. | `app.services.audit` |
| `offline_verifiable` | Indicates if an artifact can be verified without network. | `app.services.compliance` |
| `signature_placeholder` | Standard marker for pending signatures. | `app.models.security` |
| `advisory_only` | Indicates non-blocking mode for guardrails/policies. | `app.services.policy` |
| `dry_run` | Indicates simulation mode for operations. | `app.services.operations` |
| `client_id` | Unified identifier for tenants/clients. | `app.models.client` |

## Enforcement
- `scripts/validate_naming_consistency.py`: Checks for legacy or non-standard naming patterns.
- `tests/architecture/test_naming_consistency.py`: Validates consistency across critical models.
