---
owner: platform-ops
status: consolidated
---

# Release Notes: v1.9.8-platform-consolidation

## Status: Freeze, Consolidation, Optimization

This release focuses on **Platform Consolidation**, improving maintainability, supportability, and operational clarity without introducing a new major domain. The release packages freeze checks, supported-surface governance, runtime-profile controls, supportability tooling, and performance cleanup into a single stabilization line.

## Release Intent

- Freeze the platform around the `v1.9.7-compliance-readiness` baseline.
- Reduce complexity and startup overhead inside existing admin and operations areas.
- Increase supportability without widening tenant-facing product scope.
- Keep compliance, attestation, and advanced trust controls in advisory/readiness positioning unless explicitly stated otherwise.

## Highlights

### 1. Supportability Pack
- **Diagnostic Bundles**: Sanitized support bundles containing logs, health status, and system metadata for operator troubleshooting.
- **Secure Redaction**: Built-in engine to mask API keys, tokens, and sensitive URLs in all exported diagnostic data.
- **Support API**: Admin-gated endpoints for triggering and downloading bundles.
- **CLI Tool**: `scripts/generate-support-bundle.sh` for local operational use.

### 2. Performance Optimization
- **Lazy Loading**: Deferred router imports in the Control Plane reduce startup overhead and keep optional surfaces opt-in.
- **Latency Improvements**: Core health and metrics endpoints were streamlined as part of operational cleanup.
- **Resource Footprint**: Reduced idle memory usage by avoiding unnecessary service instantiation during startup.

### 3. Consolidation & Hardening
- **Refactored Main Entrypoint**: Cleaner, more modular router management in `app.main`.
- **Performance Baseline**: Integrated regression validation for system latency and import times.
- **Platform Freeze**: Automated checks enforce no new top-level domain growth without explicit exception handling.
- **Complexity Governance**: Complexity reporting, supported-surface metadata, and script manifests are now part of release hygiene.

## What's Inside

| Component | Status | Description |
|-----------|--------|-------------|
| Support Bundle | **Active** | Sanitized system snapshot for operator diagnostics |
| Lazy Router Loading | **Enabled** | Defer heavy imports until needed |
| Runtime Profiles | **Active** | Operator-controlled profile catalog with dry-run by default |
| Performance Baseline | **Active** | Automated script for performance gating |
| Supported Surface | **Active** | Explicit maturity mapping for supported, advisory, experimental, and placeholder areas |

## Domain Impact

`v1.9.8-platform-consolidation` does **not** introduce a new large bounded context. The release stays within existing admin, operations, runtime, and governance surfaces. New supportability and profiling endpoints are treated as consolidation of those existing areas and remain subject to the platform freeze rules.

## Required Validation

The release line is intended to pass the following commands as part of its gate:

```bash
make test
make validate-quick
make security
make stabilization-check
make operational-readiness
make compliance-check
make platform-freeze-check
make complexity-report
make release-gate TAG=v1.9.8-platform-consolidation
bash scripts/check-secrets.sh --all
scripts/check-alembic-integrity.sh
```

## Validation Summary

- **Security**: Release validation must continue to reject real secrets, `.env` files, prompts, and documents in versioned artifacts.
- **Supportability**: Support bundles, supported-surface metadata, and runtime-profile tooling are documented and operator-gated.
- **Stability**: No new major domain is introduced by this release line.
- **Offline-First**: All diagnostic and optimization features work without internet connectivity.
- **Positioning**: SOC 2 / ISO content remains readiness-oriented, advisory remains advisory, and experimental remains experimental.

---
*Consolidating the platform foundation without expanding its architectural surface.*
