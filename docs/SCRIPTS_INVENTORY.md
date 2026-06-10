# Scripts Inventory

This inventory classifies the live `scripts/` tree by support intent. It is the reference companion to [operations/script-governance.md](operations/script-governance.md).

## Classification Model

| Class | Meaning |
| --- | --- |
| `operational` | Operator-facing commands used to install, run, upgrade, back up, or diagnose supported surfaces |
| `validation` | Deterministic checks used by local validation or CI for supported surfaces |
| `release` | Current release engineering automation kept for active release lines |
| `legacy` | Historical or unsupported flows moved to `scripts/archive/` and excluded from supported CI |

## Operational

| Path | Notes |
| --- | --- |
| `scripts/deploy/` | Supported deploy, install, profile, lifecycle, and activation commands |
| `scripts/backup/` | Supported backup, restore, retention, and redaction commands |
| `scripts/dev/configure-local-wizard.sh` | Supported local bootstrap helper |
| `scripts/dev/generate-support-bundle.sh` | Supported diagnostics helper |
| `scripts/dev/status.sh` | Supported operator status entrypoint |
| `scripts/dev/runtime-node-*.sh` | Supported runtime node operational helpers |

## Validation

| Path | Notes |
| --- | --- |
| `scripts/validators/check-supported-surface.sh` | Supported surface policy gate |
| `scripts/validators/check_supported_surface.py` | Supported surface policy implementation |
| `scripts/validators/check-doc-consistency.py` | Canonical docs consistency gate |
| `scripts/validators/validate_platform_documentation.py` | Documentation validation |
| `scripts/validators/check-secrets.sh` | Repo secret scan used in CI |
| `scripts/validators/platform-freeze-check.*` | Surface growth guardrail |
| `scripts/validators/check-feature-flags-integrity.*` | Feature-flag integrity guardrail |
| `scripts/validators/validate-llm-harness.sh` | Harness validation kept outside supported-surface CI |

## Release

| Path | Notes |
| --- | --- |
| `scripts/release/release-gate.sh` | Current release gate |
| `scripts/release/compliance-release-gate.sh` | Current release compliance gate |
| `scripts/release/create-release-bundle.sh` | Current bundle assembly |
| `scripts/release/generate_release_baseline.py` | Current release baseline generation |
| `scripts/release/generate-sbom.sh` | Current SBOM generation |
| `scripts/release/sign-release-artifacts.sh` | Current signing flow |
| `scripts/release/upload_release_artifacts.sh` | Current artifact upload |
| `scripts/release/rollback-release.sh` | Current release rollback helper |

## Legacy

The following flows were archived because they target retired release lines or unsupported validation surfaces:

| Path | Archived Reason |
| --- | --- |
| `scripts/archive/legacy/audit-v1.6-release-line.sh` | Historical v1.6 release audit |
| `scripts/archive/legacy/validate-v1.6-release-line-audit.sh` | Historical v1.6 validation |
| `scripts/archive/legacy/validate-v1.7-release-checklist.sh` | Historical v1.7 checklist gate |
| `scripts/archive/legacy/generate-v1.7-release-checklist-status.sh` | Historical v1.7 report generator |
| `scripts/archive/legacy/validate-security-cleanup-v1.5.4.sh` | Historical v1.5.4 cleanup validation |
| `scripts/archive/legacy/validate-readiness-cleanup-v1.6.3.sh` | Historical v1.6.3 readiness validation |
| `scripts/archive/release/generate-release-history.sh` | Release-history generator for archived notes |

## Notes

- `scripts/artifacts/` is output, not supported automation.
- `scripts/llm_harness/` remains an internal codebase and is not treated as a supported product surface by the main CI workflow.
- Additional one-off developer helpers under `scripts/dev/` are intentionally not treated as canonical operator entrypoints.
