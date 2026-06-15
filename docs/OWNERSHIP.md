# Project Ownership

This document defines the areas of responsibility for the LLM Inference Stack.

## Domain Ownership

| Domain | Scope | Primary Owners |
|--------|-------|----------------|
| **Backend / Control Plane** | `control_plane/`, `scripts/llm_harness/` | @owner1, @owner2 |
| **Frontend Admin** | `frontend/admin/` | @owner1 |
| **Frontend Client** | `frontend/client/` | @owner2 |
| **Agents / Runtime** | `control_plane/app/services/agents/` | @owner1, @owner2 |
| **Billing / Payments** | `control_plane/app/services/billing/` | @owner2 |
| **Security / Compliance** | `compliance/`, `scripts/validators/` | @owner1 |
| **Infra / CI** | `.github/`, `.gitlab/`, `docker/`, `deploy/` | @owner1, @owner2 |

## Governance

- **Architectural Changes**: Require approval from at least two owners.
- **Security Patches**: Can be merged by any owner after a successful security scan.
- **Releases**: Must be coordinated between Domain Owners of affected areas.
