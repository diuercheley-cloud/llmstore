# Domain Boundaries Policy

## Overview
This document defines the Bounded Contexts within the `control_plane/app` backend and enforces strict architectural dependency rules to minimize coupling and prevent circular dependencies.

## Bounded Contexts
- **core**: Fundamental infrastructure, logging, security, configuration.
- **identity**: Authentication, authorization, RBAC, API keys.
- **billing**: Payments, reconciliation, customer accounting.
- **agents**: Agent orchestration, planning, execution, tools.
- **rag**: Knowledge base management, retrieval, embedding.
- **observability**: Metrics, tracing, logging, audit trails.
- **commercial**: Governance, compliance, infrastructure policies.
- **integrations**: External SaaS connectors, adapters.

## Dependency Rules
| Source Module | Allowed Dependencies | Prohibited Dependencies |
| :--- | :--- | :--- |
| **API** | services, schemas | core (internal details) |
| **Services** | core, schemas, models | api |
| **Models** | core | services, api |
| **Core** | - | api, services, models |

*Note: Rules are enforced by `tests/architecture/test_domain_dependencies.py`.*
