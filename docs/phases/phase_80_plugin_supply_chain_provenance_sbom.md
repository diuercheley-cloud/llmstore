# Phase 80: Plugin Supply-Chain Provenance & SBOM Placeholder Framework

Phase 80 adds a deterministic and offline-first plugin supply-chain framework on top of the Phase 79 plugin runtime. The implementation records provenance, emits SBOM placeholders, tracks artifact lineage, validates dependency governance policies, supports replay verification, and generates deterministic receipts without executing real plugins.

## Scope

- Plugin provenance records scoped by tenant.
- SBOM placeholder framework with deterministic hashes.
- Artifact lineage and replay-verifiable lineage tracking.
- Dependency governance and denied dependency classes.
- Placeholder signature records and deterministic receipts.
- Federation-safe provenance handling for offline verification.
- Admin API and dashboard markers.
- Documentation, validation script, migration, and tests.

## Non-Scope

- No real plugin execution.
- No real signing or cryptographic certification.
- No formal complete SBOM output.
- No subprocess or shell-based installers inside the Phase 80 services.
- No SaaS or cloud dependency.
- No external dependency resolver or package manager.
- No formal supply-chain certification claims.

## Guarantees

- SHA-256 deterministic hashing only.
- Client-scoped persistence for every record.
- Replay verification based on canonical JSON payloads.
- PostgreSQL-compatible models with SQLite-safe migration helpers.
- No plaintext secret storage in audit events or receipts.
- Offline-first provenance only.

## Data Model

- `PluginProvenanceRecord`
- `PluginSBOMPlaceholder`
- `PluginArtifactLineage`
- `DependencyGovernancePolicy`
- `PluginDependencyVerification`
- `PluginSignedArtifactPlaceholder`
- `PluginSupplyChainReceipt`

## Operators Notes

- SBOM output is explicitly a placeholder SBOM only.
- Signature material is explicitly a placeholder and not real artifact signing.
- Dependency validation checks metadata classes only and does not resolve or install packages.
- Replay verification and lineage verification are deterministic metadata checks intended for audit and offline replay.
