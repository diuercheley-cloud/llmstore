---
owner: platform-ops
status: consolidated
---

# Usage Dashboard

## Surface Status

- `GET /admin/usage`: `supported`
- `GET /admin/usage/by-client`: `supported`
- `GET /admin/usage/by-model`: `supported`
- `GET /admin/usage/summary`: `supported`
- `GET /admin/usage/{client_id}/summary`: `supported`
- `GET /admin/runtime/summary`: `supported`

## Overview

The usage dashboard is a supported operator surface for tenant usage, billing previews, backend health rollups, and runtime summary views.

## Notes

- Billing figures use real persisted counters plus invoice preview data.
- `runtime/summary` is read-only and aggregates health, readiness, security, queue, RAG, TTS, and reproducibility signals.
- No dry-run or placeholder path is exposed by these endpoints.
