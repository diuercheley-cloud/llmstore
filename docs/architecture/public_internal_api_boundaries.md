## Public And Internal API Boundaries

Public domain APIs:
- `contracts.py`
- `events.py`

Internal domain files:
- `schemas.py`
- `ownership.md`
- domain-specific implementation modules

Boundary policy:
- peer domains may depend on contracts and events only
- internal schemas are owned by the domain and must not be imported cross-domain
- API routers should expose sanitized summaries rather than raw internal persistence shapes when practical

This rule exists to keep Phase 82 deterministic and maintainable while real runtime, plugin, and crypto execution remain intentionally out of scope.
