# Semantic Version Governance Policy

## Purpose

This policy defines semantic version governance for APIs, schemas, extension contracts, governance artifacts, and replay-sensitive platform behavior, with explicit treatment of offline compatibility, determinism, and tenant isolation.

## Versioning Rules

- `MAJOR` changes break compatibility, remove accepted behavior, or require coordinated migration.
- `MINOR` changes add backward-compatible capabilities, optional fields, or additive governance metadata.
- `PATCH` changes preserve compatibility and correct defects, wording, or non-breaking validation logic.

## Breaking Change Rules

A change is breaking when it modifies accepted interfaces, required schema fields, replay interpretation, tenant-visible behavior, extension ABI expectations, or federation exchange semantics in a way older consumers cannot safely process.

## Phase Compatibility

- Earlier phases may be documented as historical context, but current governance must not silently reinterpret accepted artifacts from prior phases.
- A later phase may tighten validation only when migration and replay expectations are explicit.
- Phase-to-phase compatibility statements must describe upgrade, downgrade, and mixed-version expectations.

## Migration Expectations

- Every `MAJOR` change needs a migration plan.
- Every deprecation must identify replacement behavior.
- Offline operators must have a migration path that does not require mandatory SaaS or cloud services.

## Deprecation Window

Deprecations should provide a documented review window before removal unless a security issue requires faster action. The window must define operator notice, replay interpretation, and compatibility handling.

## Replay Compatibility Requirements

- Historical receipts, governance artifacts, and compatibility records must remain interpretable.
- Determinism-sensitive changes must state whether replays remain bitwise-stable, semantically stable, or version-gated.
- Tenant isolation must be preserved during mixed-version replay and migration processing.
