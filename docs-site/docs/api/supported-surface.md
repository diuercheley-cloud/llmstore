<!-- synced_from: docs/api/supported-api-surface.md -->

> Source of truth: `docs/api/supported-api-surface.md`

---
owner: platform-ops
status: consolidated
---

# Supported API Surface

This document defines API lifecycle semantics. The endpoint inventory itself is generated in [../API_REFERENCE.md](../reference/api-reference.md), while capability-level production claims remain governed by [../PRODUCT_SURFACE.md](../reference/product-surface.md).

## API Classifications

The platform divides its routes into governance categories:

1. **`supported`**:
   - Production-ready endpoints with strict backward compatibility guarantees.
   - Example: `/v1/models`, `/v1/chat/completions`.
   
2. **`beta`**:
   - Functional but subject to rapid evolutionary changes. Safe for pilot deployments.
   - Example: New agentic endpoints like `/v1/agents`.

3. **`deprecated`**:
   - Outdated endpoints slated for eventual removal. Operators are encouraged to migrate to replacements.
   - Example: Legacy `/admin/models/runtime` routes (replaced by `/admin/models/lifecycle`).

4. **`internal`**:
   - Operations-specific endpoints used exclusively by internal services and operators. No external compatibility guarantees. Requires RBAC/admin auth and is not listed in public API docs.
   - Example: `/openapi.json`, `/metrics`.

5. **`experimental`**:
   - Early-stage, opt-in capabilities. Experimental routes *must* declare a `docs_url` link in `config/api-surface.yaml` to ensure compliance.
   - Example: New/unstable trial interfaces.

6. **`removed_candidate`**:
   - Dead endpoints that have been removed from the active registry and no longer exist in the codebase.
   - Example: Unreferenced legacy beta endpoints.

## Response Headers

To facilitate runtime discovery of deprecations, the system returns:
- `X-API-Surface-Status`: The classification status of the matched route.
- `X-Deprecated-Endpoint: true`: Injected only when the status is `deprecated`.
- `X-Replacement-Endpoint`: Indicates the recommended migration path (if defined).
