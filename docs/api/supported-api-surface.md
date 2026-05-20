# Supported API Surface Document

This document outlines the API surface classifications for the `llm-inference-stack` platform, establishing clear support levels for all client and administrative endpoints.

## API Classifications

The platform divides its routes into four official governance categories:

1. **`supported`**:
   - Production-ready endpoints with strict backward compatibility guarantees.
   - Example: `/v1/models`, `/v1/chat/completions`.
   
2. **`deprecated`**:
   - Outdated endpoints slated for eventual removal. Operators are encouraged to migrate to replacements.
   - Example: Legacy `/admin/models/runtime` routes (replaced by `/admin/models/lifecycle`).

3. **`internal`**:
   - Operations-specific endpoints used exclusively by internal services and operators. No external compatibility guarantees.
   - Example: `/openapi.json`, `/metrics`.

4. **`experimental`**:
   - Early-stage, opt-in capabilities. Experimental routes *must* declare a `docs_url` link in `config/api-surface.yaml` to ensure compliance.
   - Example: New/unstable trial interfaces.

---

## Response Headers

To facilitate runtime discovery of deprecations, the system returns:
- `X-API-Surface-Status`: The classification status of the matched route.
- `X-Deprecated-Endpoint: true`: Injected only when the status is `deprecated`.
- `X-Replacement-Endpoint`: Indicates the recommended migration path (if defined).
