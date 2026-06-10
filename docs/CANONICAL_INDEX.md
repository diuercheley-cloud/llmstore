---
owner: platform-ops
status: canonical
---

# Canonical Documentation Index

This index is the source of truth for documentation classification inside `docs/`.

## Audit Summary

| Classification | Scope |
| --- | --- |
| canonical | Operator entrypoints and policy docs that may be linked from `README.md` |
| reference generated | Generated inventories derived from code or config and safe to trust only after regeneration |
| historical release | Release notes, phase snapshots, and version-specific records kept only for history |
| deprecated | Older flows preserved for context but not part of the supported surface |
| duplicate | Superseded summaries replaced by more specific canonical docs |

## Canonical

| Path | Scope |
| --- | --- |
| [../README.md](../README.md) | Product posture, supported-surface summary, entrypoint links |
| [quickstart.md](quickstart.md) | Fast local start |
| [INSTALL.md](INSTALL.md) | Installation steps |
| [index.md](index.md) | Canonical navigation page |
| [OPENAI_COMPATIBILITY.md](OPENAI_COMPATIBILITY.md) | Canonical API compatibility statement |
| [platform/supported-surface.md](platform/supported-surface.md) | Lifecycle policy for supported surfaces |
| [support/supported-surface-area.md](support/supported-surface-area.md) | Supported-surface policy and readiness criteria |
| [api/supported-api-surface.md](api/supported-api-surface.md) | Public and operator API classifications |
| [operations/platform_runbook.md](operations/platform_runbook.md) | Supported operational runbook |
| [deployment/appliance-deploy.md](deployment/appliance-deploy.md) | Supported appliance deployment path |
| [deployment/kubernetes-deploy.md](deployment/kubernetes-deploy.md) | Supported Kubernetes deployment path when explicitly enabled |
| [support/troubleshooting.md](support/troubleshooting.md) | Operator troubleshooting |
| [support/support-bundle.md](support/support-bundle.md) | Supported diagnostics workflow |
| [PRODUCT_SURFACE.md](PRODUCT_SURFACE.md) | Capability status source of truth generated from `config/supported-surface.yaml` |

## Reference Generated

| Path | Scope |
| --- | --- |
| [API_REFERENCE.md](API_REFERENCE.md) | Endpoint inventory generated from `config/api-surface.yaml` |
| [CONFIGURATION_REFERENCE.md](CONFIGURATION_REFERENCE.md) | Runtime configuration inventory generated from `BaseAppConfig` |
| [FLAGS_INVENTORY.md](FLAGS_INVENTORY.md) | Feature flag inventory generated from the registry and settings model |
| [PRODUCT_SURFACE.md](PRODUCT_SURFACE.md) | Product capability matrix generated from `config/supported-surface.yaml` |
| [SCRIPTS_INVENTORY.md](SCRIPTS_INVENTORY.md) | Reference catalog for active and archived scripts |
| [operations/script-governance.md](operations/script-governance.md) | Script lifecycle and ownership policy |

## Reference

These docs support the canonical set but are not primary entrypoints.

| Path | Scope |
| --- | --- |
| [architecture/platform_overview.md](architecture/platform_overview.md) | Architecture summary and constraints |
| [architecture/platform_guarantees_and_limitations.md](architecture/platform_guarantees_and_limitations.md) | Explicit limitations and claims policy support |
| [architecture/platform_domain_map.md](architecture/platform_domain_map.md) | Structural reference |
| [architecture/platform_validation_workflows.md](architecture/platform_validation_workflows.md) | Validation flow reference |
| [ci/github-actions.md](ci/github-actions.md) | CI implementation notes for supported jobs |

## Release Historical

Historical release notes and version-specific cleanup records live under [archive/releases/](archive/releases/).

## Deprecated

Deprecated operational notes moved during this cleanup live under [archive/deprecated/](archive/deprecated/).

| Path | Replaced By |
| --- | --- |
| `archive/deprecated/MIGRATIONS_SQUASH.md` | Generated config and product references; no supported migration narrative remains at repo root |
| `archive/deprecated/MIGRATION_POLICY.md` | `PRODUCT_SURFACE.md` and code-owned migration validators |
| `archive/deprecated/MIGRATION_INDEX.md` | Historical only |
| `archive/deprecated/LOCALHOST.md` | `quickstart.md` and deployment guides |

## Duplicate

Superseded summaries replaced by more specific canonical docs live under [archive/duplicates/](archive/duplicates/).

| Path | Replaced By |
| --- | --- |
| `archive/duplicates/SDKS.md` | `docs/sdk/agents-node.md` and `docs/sdk/agents-python.md` |
