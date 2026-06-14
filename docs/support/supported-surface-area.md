# Supported Surface Area

This document defines how support claims are made. Capability status is sourced from the
canonical machine-readable registry and must not be duplicated manually.

## Source Of Truth

| Artifact | Location | Purpose |
|---|---|---|
| Capability registry | `config/supported-surface.yaml` | Machine-readable capability definitions with status, flags, limitations |
| Feature flag registry | `config/feature-flags.yaml` | Every feature flag with defaults, owner, area, risk, dependencies |
| Public API endpoint | `GET /public/capabilities` | Dynamically serves registry data, filtered by enabled feature flags |
| Auto-generated docs | `docs/generated/PRODUCT_SURFACE.md` | Compact matrix of capability ID, status, support, owner |
| Human-readable docs | `docs/PRODUCT_SURFACE.md` | Status summary, lifecycle tiers, capability matrix |

No per-capability status list exists in `README.md`, this page, or `docs/platform/supported-surface.md`.
The `GET /public/capabilities` endpoint is the canonical live view of the supported surface area.

## Lifecycle Tiers

Status values in `config/supported-surface.yaml` and the `capability_level` field in API responses:

| Tier | `capability_level` | `status` (API) | Meaning |
|---|---|---|---|
| `production_core` | `core` | `supported` | No mock in critical path. Enabled by default or production-gated. |
| `production_optional` | `supported` | `supported` | Production-quality but opt-in. Mock-safe defaults. Gated behind flags. |
| `beta` | `beta` | `beta` | Feature-complete but evolving. Not unconditional production claim. |
| `experimental` | `experimental` | `experimental` | Early stage. Heavy mock usage. May change without notice. |
| `internal` | *(excluded from public)* | *(excluded)* | Internal tools. Not customer-facing. |
| `deprecated` | `deprecated` | `deprecated` | No longer maintained. Will be removed in future releases. |

## Feature Flag Enforcement

The `GET /public/capabilities` endpoint:

1. Loads all capabilities from `config/supported-surface.yaml`.
2. Excludes capabilities with `status: internal`.
3. Checks each capability's `feature_flag` and `additional_flags` against current settings.
4. **Omits** capabilities whose feature flag(s) resolve to `false`.
5. Returns each capability with accurate `status`, `capability_level`, `limitations`, `docs_url`.

This ensures that **no partial or disabled feature is advertised as `supported` or `core`**.

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

## Deprecation Lifecycle Policy

Every deprecated surface **MUST** have a documented removal timeline:

| Field | Required | Description |
|---|---|---|
| `owner` | Yes | Team responsible for the surface |
| `replacement` | Yes | Migration path or replacement |
| `sunset_date` | Yes (or `removal_version`) | Target removal date (`YYYY-MM-DD`) |
| `removal_version` | Yes (or `sunset_date`) | Target removal version (e.g. `v3.0`) |

### CI Validation

Every new surface marked as `deprecated` **without a defined deadline** will be blocked by the validator:

```bash
python3 scripts/validate_deprecated_surface.py
```

The complete inventory of deprecated surfaces is maintained in:

- `docs/generated/deprecated_surface_inventory.md` (auto-generated)
- `config/api-surface.yaml` (endpoints)
- `config/supported-surface.yaml` (capabilities)
- `config/feature-flags.yaml` (feature flags)

### Extension Approval Criteria

1. Written justification from the owner.
2. New date must not exceed 2 releases beyond the original.
3. Approval from `platform-ops` via PR review.
4. Update of inventory and deadline in the corresponding YAML.
