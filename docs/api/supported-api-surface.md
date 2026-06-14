---
owner: platform-ops
status: consolidated
---

# Supported API Surface

This document defines API lifecycle semantics. The endpoint inventory itself is generated in [../API_REFERENCE.md](../API_REFERENCE.md), while capability-level production claims remain governed by [../PRODUCT_SURFACE.md](../PRODUCT_SURFACE.md).

## API Classifications

The platform divides its routes into governance categories:

1. **`supported`**:
   - Production-ready endpoints with strict backward compatibility guarantees.
   - Example: `/v1/models`, `/v1/chat/completions`.
   
2. **`beta`**:
   - Functional but subject to rapid evolutionary changes. Safe for pilot deployments.
   - Example: opt-in operator surfaces such as voice session management or backend lifecycle controls.

3. **`experimental`**:
   - Early-stage, opt-in capabilities with incomplete operational guarantees.
   - Example: evolving control surfaces that are available for evaluation but may still change quickly.

4. **`simulated`**:
   - Endpoints that intentionally execute dry-run or placeholder behavior with no real side effects.
   - Example: simulation-only remediation execution or WebRTC signaling placeholders.

5. **`deprecated`**:
   - Outdated endpoints slated for eventual removal. Operators are encouraged to migrate to replacements.
   - Example: Legacy `/admin/models/runtime` routes (replaced by `/admin/models/lifecycle`).

## Response Headers

To facilitate runtime discovery of deprecations, the system returns:
- `X-API-Surface-Status`: The classification status of the matched route.
- `X-Deprecated-Endpoint: true`: Injected only when the status is `deprecated`.
- `X-Replacement-Endpoint`: Indicates the recommended migration path (if defined).
