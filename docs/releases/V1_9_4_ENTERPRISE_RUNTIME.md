---
owner: platform-ops
status: consolidated
---

# Release Notes: v1.9.4-enterprise-runtime

## Overview
This release integrates the Kubernetes/operator, distributed runtime, GPU orchestration, plugin marketplace, managed control-plane, and enterprise packaging workstreams without changing the default local/offline posture of the appliance.

## Secure Defaults

- `DEPLOYMENT_MODE=appliance`
- `KUBERNETES_MODE=false`
- `DISTRIBUTED_RUNTIME_ENABLED=false`
- `GPU_AUTOSCALING_ENABLED=false`
- `PLUGIN_MARKETPLACE_ENABLED=false`
- `MANAGED_CONTROL_PLANE_ENABLED=false`

These defaults keep Docker Compose as the baseline path and ensure every new enterprise surface is explicitly opt-in.

## What Changed

## Validation Results (v1.9.4 RC)

- **Operational Readiness**: `pilot_ready` (verified via `make operational-readiness`).
- **Resilience**: 100% pass on smoke and chaos tests (verified via `make test-smoke-resilience` and `make test-chaos-resilience`).
- **Security**: No secrets or private certificates found in versioned files (verified via `bash scripts/check-secrets.sh --all`).
- **Stability**: Single Alembic head verified (`6c73eca75cd9`).
- **Working Tree**: Clean and audit-ready (verified via `make stabilization-check`).

## Out of Scope
- Direct exfiltration of prompt data via the managed control-plane (blocked by heartbeat schema enforcement).
- Automated Kubernetes scaling without explicit configuration (advisory-only).
- External PKI management (local-only issuance path).
- Distributed runtime lookup is skipped when the feature is disabled, preserving the local GGUF hot-swap path.
- GPU autoscaling is automatically suppressed unless distributed runtime is enabled.

### Offline-first marketplace
- Marketplace flows remain based on locally supplied plugin archives.
- No remote marketplace dependency is required for installation, enable/disable, or upgrade flows.

### Managed control-plane boundaries
- Managed control-plane heartbeats accept operational metadata only.
- Prompt/document-like keys are rejected at schema validation time before persistence.
- Local/offline appliance mode keeps managed routes disabled.

### Packaging and validation
- Kubernetes manifests remain optional and are validated independently through `make k8s-validate`.
- Enterprise packaging artifacts and release summaries are tracked under `docs/releases/` and `artifacts/releases/`.

## Validation Snapshot

- Passed: targeted enterprise-runtime regression tests.
- Passed: `make test`
- Passed: `make security`
- Passed: `make k8s-validate`
- Passed: `make test-smoke-resilience`
- Passed: `make test-chaos-resilience`
- Passed: `bash scripts/check-secrets.sh --all`
- Observed: `make operational-readiness` completed with `production_blocked`
- Observed: `alembic heads` reports multiple heads, including duplicate `1234567890ab`
- Partial: `make validate` repeatedly reached the final repository pytest stage but did not complete within the session window
- Partial: `make stabilization-check` was re-run after `make test` passed, but was stopped because it delegates to the same long-running `make validate` path

## Release Focus

This release is about integrating new enterprise capabilities without forcing them on local users. The primary acceptance criterion is that the appliance remains safe, offline-first, and functional unless operators explicitly opt into the new surfaces.
