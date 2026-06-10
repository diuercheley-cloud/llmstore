# Supported Surface Area

This document defines how support claims are made. It does not enumerate capability status manually.

## Source Of Truth

- Capability status and support level live in [../PRODUCT_SURFACE.md](../PRODUCT_SURFACE.md).
- The underlying machine-readable source is `config/supported-surface.yaml`.
- `README.md`, this page, and `docs/platform/supported-surface.md` must not restate per-capability status lists manually.

## Readiness Criteria

### `production_core`

1. **No Mocking**: Simulated success paths are blocked in production environments.
2. **Policy Enforcement**: Comprehensive tenant isolation and RBAC.
3. **Audit Trail**: Every critical action generates a persistent audit event.
4. **Verified Logic**: Automated test suites cover compliance and security.
5. **Documentation**: Clear operational and security guides.

### `production_optional`

Production-quality capability, but still opt-in and expected to ship behind explicit flags or profiles.

### `beta`

Feature-complete but still evolving. Suitable for pilot evaluation, not an unconditional production claim.

### `experimental`

Early-stage surface. No production claim.

### `deprecated`

Supported only for migration or historical compatibility until removal.
