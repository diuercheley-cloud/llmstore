# Architecture Rules

These rules are enforced by `tests/architecture/test_dependencies.py`.
The repository now carries `grimp` as the architecture-test dependency, while the
current checks use a pytest-based AST scan because `app.api` and `app.services`
still rely heavily on namespace-style directories without package markers.

## Active rules

1. `app.services` must not import `app.api`.
2. `app.models` must not import `app.services`.
3. `app.api` must not import infrastructure internals directly.
4. `billing` must not depend on `agents` directly.
5. `audit` is a permitted cross-cutting dependency.

## Scope

- Rule 3 currently treats the following namespaces as infrastructure internals:
  - `app.db`
  - `app.services.cache.semantic_cache_redis`
  - `app.services.inference.backends`
  - `app.services.routing.infra_adapters`
- Rule 4 currently applies to:
  - `app.services.billing`
  - `app.domains.billing`
  - `app.models.billing`

## Resolved exception

- `ARCH-API-INFRA-001`
  - Rule: `app.api` must not import infrastructure internals directly.
  - Status: resolved. The API now consumes runtime dependency facades from `app.services`.
  - Previously affected areas:
    - `app.db`
    - `app.services.cache.semantic_cache_redis`
    - `app.services.inference.backends`
    - `app.services.routing.infra_adapters`
  - Remediation date: 2026-06-12.

## Remediation guidance

- Prefer moving shared factories into `app.services` or a dedicated application-service module instead of importing from `app.api`.
- Keep ORM models free of service-layer behavior.
- Expose stable service interfaces to the API layer instead of direct database/session or backend-adapter access.
