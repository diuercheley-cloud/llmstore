---
owner: platform-ops
status: consolidated
---

# Dependency Graph Hardening

## Architecture Rules
- **Bounded Context Isolation**: Each domain service must only depend on its own models and the shared kernel.
- **Top-Down Flow**: `app.api` can import `app.services`, but `app.services` must NEVER import `app.api`.
- **No Circular Dependencies**: Circular imports between services are blocked.
- **Shared Kernel**: Only common utilities and base classes in `app.db` or `app.core` are globally accessible.

## Domain Boundaries
- `governance`
- `inference`
- `billing`
- `security`
- `operations`

## Enforcement
- `scripts/validators/validate_dependency_graph.py`: Checks for illegal cross-domain imports.
- `tests/architecture/test_dependency_graph_hardening.py`: Validates architecture invariants.
