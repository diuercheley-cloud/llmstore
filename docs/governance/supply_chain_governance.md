# Supply-Chain Governance

## Purpose

This document defines supply-chain governance for dependencies, artifacts, vendoring, provenance placeholders, and build discipline, with explicit offline compatibility, determinism, and tenant isolation expectations.

## Dependency Policy

- Prefer minimal, auditable dependencies.
- New dependencies require documented purpose, update strategy, and risk review.
- Dependencies that cannot be evaluated offline require explicit justification and mitigation.

## Signed Artifact Placeholder Policy

Artifact signing language in this repository is placeholder-oriented unless backed by implemented controls. Placeholder metadata must not be presented as production trust proof.

## Denied Dependency Classes

- mandatory remote-only build dependencies
- packages with undeclared telemetry by default
- opaque auto-updating binaries without review
- dependencies requiring permanent cloud reachability for baseline operation

## Vendored and Offline Dependency Expectations

- Critical dependencies should support vendored or mirrored offline workflows.
- Offline packaging expectations must be documented for sovereign deployments.
- No mandatory SaaS or cloud service may be required for baseline governance validation.

## Telemetry and External Services

- No telemetry by default.
- No mandatory SaaS or cloud control plane.
- Optional remote services must be clearly marked as optional and disabled by default.

## Reproducible Build Expectations

- Build inputs should be pinned or otherwise constrained.
- Artifact generation should be repeatable enough for governance review.
- Determinism expectations must be documented where byte-for-byte reproduction is not possible.

## SBOM Placeholder Policy

SBOM records may exist as placeholders or partial inventories, but they must be labeled accordingly and must not imply external certification.

## Artifact Provenance Placeholder Policy

Provenance metadata may be documented as placeholders for future controls. Such metadata must not imply production-grade attestation, external approval, or hardware-backed trust.

## Tenant Isolation

Supply-chain processes must avoid cross-tenant artifact leakage, shared mutable trust state without review, and ambiguous provenance visibility.
