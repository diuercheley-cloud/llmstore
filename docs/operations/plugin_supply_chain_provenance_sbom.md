---
owner: platform-ops
status: consolidated
---

# Plugin Supply-Chain Provenance & SBOM Placeholder Framework

This operations document describes the Phase 80 framework for deterministic plugin supply-chain provenance and SBOM placeholders.

## What It Does

- Registers provenance for plugin-related artifacts without executing them.
- Generates deterministic SBOM placeholders from provided metadata.
- Validates dependency classes against local governance policy.
- Creates lineage links between parent and derived artifact hashes.
- Emits deterministic receipts and sanitized audit events.
- Supports replay verification for provenance, SBOM placeholders, and lineage.

## What It Does Not Do

- Placeholder SBOM only.
- No real signing.
- No external dependency resolver.
- No real package manager.
- No formal supply-chain certification.

## Denied Dependency Classes

The governance layer blocks these classes by default:

- `network_loaders`
- `remote_package_installers`
- `shell_based_installers`
- `dynamic_external_imports`
- `unverified_binary_artifacts`

## Replay And Audit

- Replay verification is based on canonical JSON and deterministic SHA-256 hashes.
- Audit events redact sensitive-looking keys such as `token`, `password`, `credential`, `signature`, and `payload`.
- Receipts always use `signature_placeholder` markers.

## Admin API

- `POST /admin/operations/plugin-supply-chain/provenance`
- `GET /admin/operations/plugin-supply-chain/provenance`
- `GET /admin/operations/plugin-supply-chain/provenance/{id}`
- `POST /admin/operations/plugin-supply-chain/provenance/{id}/verify`
- `POST /admin/operations/plugin-supply-chain/provenance/{id}/revoke`
- `POST /admin/operations/plugin-supply-chain/provenance/{id}/sbom`
- `POST /admin/operations/plugin-supply-chain/provenance/{id}/dependency-verify`
- `POST /admin/operations/plugin-supply-chain/provenance/{id}/lineage`
- `POST /admin/operations/plugin-supply-chain/provenance/{id}/replay-verify`
- `POST /admin/operations/plugin-supply-chain/provenance/{id}/sign-placeholder`
- `POST /admin/operations/plugin-supply-chain/provenance/{id}/receipt`

## Dashboard Warnings

- `placeholder SBOM only`
- `no real artifact signing`
- `offline-first provenance only`
