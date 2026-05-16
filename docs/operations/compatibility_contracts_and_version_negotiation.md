# Compatibility Contracts And Version Negotiation

## Overview
This module provides deterministic compatibility only controls for sovereign and federated environments. It validates semantic versions, schema versions, compatibility matrices, capability requests, feature boundaries, upgrade and downgrade paths, and deprecation state before a contract can be reused.

## Semantic Versioning
- Semantic versions are parsed offline with a local deterministic parser.
- Major-version drift is treated as incompatible.
- Same-major and same-minor versions are considered bidirectional for replay-safe negotiation.
- Same-major minor upgrades are backward compatible.

## Compatibility Matrix
- `backward`: upgrade is supported.
- `forward`: controlled warning only.
- `bidirectional`: replay-safe in both directions.
- `restricted`: negotiation is blocked.

## Negotiation Lifecycle
- Negotiation is deterministic only.
- The negotiated version is the lower compatible version.
- Incompatible sessions are marked `conflicted`.
- Replay verification is required for accepted sessions.

## Capability Negotiation
- Approved capabilities are a deterministic subset of requested capabilities.
- Denied capabilities always win.
- Restricted capabilities include `shell`, `subprocess`, `network`, `kubernetes_apply`, `proxmox_mutate`, `nomad_run`, `external_secret_read`, and `hardware_attestation_real`.

## Feature Flags
- Feature flags declare minimum and maximum supported versions.
- `deprecated_after_version` is advisory for lifecycle enforcement and documentation.
- Feature flags remain replay-safe only when bounded by compatible versions.

## Deprecation Lifecycle
- States: `proposed`, `announced`, `enforced`, `completed`.
- If `migration_required=True`, `replacement_contract` is mandatory.
- Blocked contracts cannot be negotiated.

## Verification
- Contracts, matrices, negotiation sessions, and capability results can be verified offline.
- `replay_safe` is mandatory.
- Forward compatibility warnings are allowed only as controlled warnings.

## Receipts
- Contract, negotiation, verification, and deprecation receipts contain:
- `receipt_type`
- `client_id`
- `subject_id`
- `immutable_hash`
- `payload_hash`
- `deterministic_version`
- `signature_placeholder`
- `generated_at`

## Audit Events
- `compatibility_contract_created`
- `compatibility_matrix_created`
- `version_negotiation_started`
- `version_negotiation_completed`
- `capability_negotiation_completed`
- `compatibility_verification_completed`
- `deprecation_proposed`
- `deprecation_announced`
- `deprecation_enforced`
- `compatibility_receipt_created`

## API Admin
- `POST /admin/operations/compatibility/contracts`
- `GET /admin/operations/compatibility/contracts`
- `GET /admin/operations/compatibility/contracts/{contract_id}`
- `POST /admin/operations/compatibility/matrix`
- `POST /admin/operations/compatibility/negotiate`
- `POST /admin/operations/compatibility/capabilities/negotiate`
- `POST /admin/operations/compatibility/contracts/{contract_id}/verify`
- `POST /admin/operations/compatibility/contracts/{contract_id}/deprecate`
- `GET /admin/operations/compatibility/deprecations`
- `POST /admin/operations/compatibility/contracts/{contract_id}/receipt`

## Dashboard
- Admin and portal include a section named `Compatibility Contracts & Version Negotiation`.
- The UI exposes counts and status markers only.
- No sensitive plaintext payload is exposed.

## Security Notes
- deterministic compatibility only
- offline-first
- tenant isolation required
- no external dependency resolver
- no SaaS or cloud requirement
- no real hardware-backed compatibility trust
- no real infrastructure mutation

## Limitations
- No external dependency resolution.
- No real adapter execution.
- No mandatory network calls.
- No hardware-backed trust implementation.
