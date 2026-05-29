---
owner: platform-ops
status: consolidated
---

# Feature Flag Governance and Lifecycle Policy

This document defines the governance rules, classifications, and audit processes for feature flags in the Agentic AI Platform.

---

## Life Cycle Classifications

All feature flags defined in `config/feature-flags.yaml` must be classified under one of the following categories:

| Status | Code / Env References | Description |
| :--- | :--- | :--- |
| **Active** | Required | Actively used in python code or env configuration. |
| **Experimental** | Required | Safe, opt-in features being evaluated. Must default to `false`. |
| **Deprecated** | Not Required | Features marked for deletion. Must provide `remove_after` and/or `replacement` attributes. |
| **Internal Only** | Required / Not Required | Environment control flags or internal-only platform switches. |
| **Orphaned** | None | Flags defined in the registry but never referenced. Considered a governance violation. |

---

## Validation & Quality Gates

The platform enforces strict rules to prevent "ghost" feature flags and registry inconsistencies:
1. **Metadata Enforcement**: Every flag must declare an `owner`, `area`, `status`, and `safe_default_reason` (or details).
2. **Duplication Checks**: No flag name can be defined more than once in the YAML registry.
3. **Registry Coherence**: All feature flags used in python source files or `.env.example` must be registered in `config/feature-flags.yaml`.

---

## Running Audits

Operators can run the governance auditor manually:
```bash
make feature-flag-audit
```

This task invokes the audit script `scripts/audit-feature-flags.py` which:
- Scans files and builds a metadata matrix.
- Generates the markdown report at `artifacts/platform/feature-flag-audit.md`.
- Returns an exit code of `1` if structural violations (duplicates, missing owners, or missing reasons) are found.

### Automating Cleanups
To automatically clean up orphaned flags by marking them as `deprecated` (which appends a deprecation schema):
```bash
python3 scripts/audit-feature-flags.py --fix deprecate
```

To remove them from the YAML configuration entirely:
```bash
python3 scripts/audit-feature-flags.py --fix remove
```

---

## Release Gates

The CI/CD pipeline and release gate (`make release-gate`) execute the validation automatically. Any orphaned flags will raise a `[WARNING]` in the release log, prompting the developer to deprecate or prune them.
