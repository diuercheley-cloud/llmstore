# Domain Persistence Contracts (StorageBackend by Domain)

## Overview
To reduce direct ORM access (SQLAlchemy) spread across services and APIs, we use explicit repository contracts for critical domains. This promotes decoupling, better testability, and clear boundaries.

## Permitted Dependencies
- **Services** should depend on **Repository Protocols** (defined in `contracts.py`).
- **Repositories** implement these protocols using a specific persistence engine (e.g., SQLAlchemy in `repositories.py`).
- **Models** (ORM) should ideally be encapsulated within the repositories.

## Domains

### Billing
- **Contract**: `app.domains.billing.contracts.BillingRepository`
- **Implementation**: `app.domains.billing.repositories.SqlAlchemyBillingRepository`
- **Model**: `BillingPlan`

### Auth
- **Contract**: `app.domains.auth.contracts.AuthRepository`
- **Implementation**: `app.domains.auth.repositories.SqlAlchemyAuthRepository`
- **Model**: `AdminUser`

### Audit
- **Contract**: `app.domains.audit.contracts.AuditRepository`
- **Implementation**: `app.domains.audit.repositories.SqlAlchemyAuditRepository`
- **Model**: `ImmutableAuditLog`

### Policy
- **Contract**: `app.domains.policy.contracts.PolicyRepository`
- **Implementation**: `app.domains.policy.repositories.SqlAlchemyPolicyRepository`
- **Model**: `DeterministicPolicy`

### Config
- **Contract**: `app.domains.config.contracts.ConfigRepository`
- **Implementation**: `app.domains.config.repositories.InMemoryConfigRepository` (Default)

## Migration Status
Critical services are being migrated to these contracts. Direct model access in APIs is being replaced by repository calls.

## Technical Debt / Inventory
The following areas still use direct ORM access and should be migrated:
- `app.services.billing.core.ensure_default_billing_plans`
- `app.api.admin_billing.list_billing_plans` (partially migrated)
- `app.api.governance_policy_engine_admin.list_policies` (partially migrated)
