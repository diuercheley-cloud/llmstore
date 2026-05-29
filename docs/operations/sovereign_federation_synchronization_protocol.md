---
owner: platform-ops
status: consolidated
---

# Sovereign Federation Synchronization Protocol

## Overview
The Sovereign Federation Synchronization Protocol provides deterministic synchronization primitives for federated sovereign environments without requiring a live network. Sessions, bundles, lineage links, trust negotiations, conflict resolutions, and receipts are all tenant-scoped and replay-oriented.
This phase is explicitly offline federation only and placeholder trust only.

## Federation Lifecycle
1. Register sovereign environments.
2. Evaluate placeholder trust and offline verification requirements.
3. Negotiate trust between source and target environments.
4. Create a deterministic synchronization session.
5. Export a deterministic bundle.
6. Import the bundle in an offline-first flow.
7. Verify replay and lineage.
8. Resolve conflicts deterministically or block finalization.
9. Generate receipts and audit events.

## Sync Sessions
- Session identity is deterministic.
- Logical hashes exclude timestamps.
- `replay_verifiable`, `offline_verifiable`, and `lineage_verified` are explicit session controls.
- Cross-tenant session access is blocked.

## Replay Verification
- Replay verification is mandatory.
- Replay uses SHA-256 over canonical JSON.
- No randomness, subprocess execution, or network calls are required.
- Verified trust levels still require replay-verifiable bundles.

## Lineage Verification
- Each bundle can produce a lineage link.
- Lineage verification is deterministic and offline-compatible.
- Lineage conflicts cannot be ignored.

## Trust Negotiation
- Placeholder trust only.
- `isolated` environments cannot synchronize automatically.
- `restricted` environments require manual review on conflicts.
- `verified` environments still require replay-verifiable bundles.
- `signature_placeholder` is not real trust.
- There is no hardware-backed federation trust.

## Deterministic Conflict Resolution
- Supported strategies: `reject`, `deterministic_merge`, `keep_source`, `keep_target`, `manual_review_required`.
- `deterministic_merge` is deterministic by construction.
- `replay_conflict` blocks verification.
- `manual_review_required` blocks session finalization.

## Receipts
- Receipts are available for sessions, bundles, trust negotiations, and conflict resolutions.
- Every receipt includes `receipt_type`, `client_id`, `subject_id`, `immutable_hash`, `payload_hash`, `deterministic_version`, `signature_placeholder`, and `generated_at`.

## Audit Events
- Environment registration.
- Session creation.
- Bundle export/import/verification.
- Conflict detection/resolution.
- Trust negotiation.
- Replay verification.
- Receipt generation.

Audit events sanitize sensitive payload fields and stay offline-compatible.

## API Admin
- `POST /admin/operations/federation/environments`
- `GET /admin/operations/federation/environments`
- `POST /admin/operations/federation/sessions`
- `GET /admin/operations/federation/sessions`
- `GET /admin/operations/federation/sessions/{session_id}`
- `POST /admin/operations/federation/bundles/export`
- `POST /admin/operations/federation/bundles/import`
- `POST /admin/operations/federation/bundles/{bundle_id}/verify`
- `POST /admin/operations/federation/trust-negotiate`
- `POST /admin/operations/federation/conflicts/resolve`
- `GET /admin/operations/federation/lineage/{bundle_id}`
- `POST /admin/operations/federation/sessions/{session_id}/receipt`

## Dashboard
Admin and portal dashboards expose Phase 77 counters and notices for:
- Total federation environments.
- Sync sessions.
- Verified bundles.
- Conflict count.
- Lineage verification status.
- Replay verification status.
- Trust negotiation status.
- Offline verification status.
- Receipts available.

## Security Notes
- Tenant isolation is enforced by `client_id`.
- Sensitive plaintext payloads are not exposed by audit events.
- Offline-first behavior is the default.
- Placeholder trust only.
- No hardware-backed federation trust.
- No real-time synchronization.
