# Sovereign Execution Attestation Framework

## Overview

The Sovereign Execution Attestation Framework creates deterministic placeholder attestations for operational subjects:

- workflows
- remediation plans and executions
- adapter registry decisions
- adapter promotion state
- sandbox runs
- federation bundle exchange

The design is offline-first. All verification logic is local and hash-based.

## Attestation Lifecycle

- `proposed`: reserved status for future workflows.
- `issued`: placeholder attestation generated.
- `verified`: replay, chain, and offline checks passed.
- `revoked`: admin revoked with reason.
- `expired`: reserved for future policy-driven expiration.

## Attestation Chains

Each attestation can reference a previous attestation hash. Chain links are derived deterministically from:

- client
- attestation id
- attestation hash
- previous link hash
- chain position

This gives a verifiable placeholder chain without claiming a real signature chain.

## Replay Verification

Replay verification recomputes deterministic hashes from the stored logical fields:

- attestation type
- subject type
- subject reference
- scope
- payload hash
- previous hash
- placeholder signature marker
- replay and offline flags

No randomness, subprocess execution, external network call, or ML dependency is used.

## Federation Bundles

Bundles package deterministic attestation references for export/import between offline environments. Federation uses only hash-addressable placeholder metadata. Secrets are not transported in plaintext.

## Trust Policy Engine

Trust policy evaluation blocks when:

- the attestation type is not allowed
- `signature_placeholder` is absent
- replay verification is missing
- offline verification is missing
- chain integrity requirements are not satisfied

## Receipts

Receipts exist for:

- attestations
- verification results
- chains
- federation bundles

Every receipt includes:

- `receipt_type`
- `client_id`
- `subject_id`
- `immutable_hash`
- `payload_hash`
- `deterministic_version`
- `signature_placeholder`
- `generated_at`

## Audit Events

Audit events are offline-compatible placeholder records for issue, verify, revoke, bundle import/export, replay verify, and receipt creation. Sensitive payload fields are redacted.

## Admin API

Admin endpoints live under `/admin/operations` and enforce tenant isolation with `client_id` scoping.

## Dashboard

The admin dashboard and client portal expose summary markers only:

- total attestations
- verified attestations
- revoked attestations
- federation bundles
- replay verification status
- chain integrity status
- offline verification status
- signature placeholder status
- receipts available

Both surfaces state clearly that this phase is placeholder attestation only and that no hardware-backed trust is implemented.

## Limitations

- no hardware-backed attestation
- no TPM, SGX, or SEV implementation
- no real signatures
- no confidential computing
- no formal certification claims
