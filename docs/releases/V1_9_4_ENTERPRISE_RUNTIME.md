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

### Optional runtime surfaces
- Optional routers are mounted only when their corresponding feature gates are enabled.
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
