# Supported Surface Area

This document defines how support claims are made. It does not enumerate capability status manually.

## Source Of Truth

- Capability status and support level live in [../PRODUCT_SURFACE.md](../PRODUCT_SURFACE.md).
- The underlying machine-readable source is `config/supported-surface.yaml`.
- The comprehensive API route surface is automatically generated at `generated/route_surface_manifest.json` and must not be edited manually.
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

## Deprecation Lifecycle Policy

Every deprecated surface **MUST** have a documented removal timeline:

| Field | Obrigatório | Descrição |
|---|---|---|
| `owner` | Sim | Time responsável pela superfície |
| `replacement` | Sim | Caminho de migração ou substituto |
| `sunset_date` | Sim (ou `removal_version`) | Data alvo para remoção (formato `YYYY-MM-DD`) |
| `removal_version` | Sim (ou `sunset_date`) | Versão alvo para remoção (ex: `v3.0`) |

### Validação CI

Toda nova superfície marcada como `deprecated` **sem prazo definido** será bloqueada pelo validador:

```bash
python3 scripts/validate_deprecated_surface.py
```

O inventário completo de superfícies deprecadas é mantido em:

- `docs/generated/deprecated_surface_inventory.md` (auto-gerado)
- `config/api-surface.yaml` (endpoints)
- `config/supported-surface.yaml` (capabilities)
- `config/feature-flags.yaml` (feature flags)

### Critérios de Aprovação para Extensão de Prazo

1. Justificativa por escrito do owner.
2. Nova data não pode exceder 2 releases além da original.
3. Aprovação do `platform-ops` via PR review.
4. Atualização do inventário e do prazo no YAML correspondente.
