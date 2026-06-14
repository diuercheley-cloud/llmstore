---
owner: platform-ops
status: consolidated
---

# Backend Lifecycle

## Surface Status

- `POST /admin/backends/{backend_id}/start`: `beta`
- `POST /admin/backends/{backend_id}/stop`: `beta`
- `POST /admin/backends/{backend_id}/restart`: `beta`
- `GET /admin/backends/{backend_id}/lifecycle/observed`: `beta`
- `POST /admin/backends/{backend_id}/lifecycle/reconcile`: `beta`
- `POST /admin/backends/lifecycle/reconcile-all`: `beta`
- `GET /admin/backends/lifecycle/drift-history`: `beta`

## Overview

Backend lifecycle APIs provide operator controls for backend process state, observed-vs-desired reconciliation, and drift tracking.

## Constraints

- Capability depends on the lifecycle provider selected for each backend.
- Docker-backed providers currently expose the broadest lifecycle coverage.
- Unsupported providers fail closed with explicit `ProviderUnavailableError` responses instead of simulating success.

## Why `beta`

The lifecycle manager is real and stateful, but provider support is still uneven across `docker`, `local_process`, and `kubernetes`. The surface is therefore classified as `beta`, not `supported`.
