---
owner: platform-ops
status: consolidated
---

# Operational Script Governance

This document establishes the official governance policy for operational and management scripts in the `llm-inference-stack` platform.

## Script Classifications

Scripts are classified by support intent. The canonical reference is [docs/SCRIPTS_INVENTORY.md](../SCRIPTS_INVENTORY.md).

1. **`operational`**
   - Supported operator commands for install, deploy, lifecycle, backup, restore, and diagnostics.
   - These are the only scripts that should appear as recommended execution paths in canonical docs.

2. **`validation`**
   - Deterministic checks used by CI or local validation for supported surfaces.
   - Validation scripts must fail closed when their required inputs or docs are missing.

3. **`release`**
   - Current release engineering automation for active release lines only.
   - Version-specific release scripts become `legacy` once the line is retired.

4. **`legacy`**
   - Historical or unsupported flows moved to `scripts/archive/`.
   - Legacy scripts are not part of supported CI and must not be linked from the main `README.md` as recommended workflows.

---

## Safety and Environmental Requirements

Scripts in the supported set must follow these rules:

- Destructive operational scripts require explicit confirmation or an environment-gated non-interactive override.
- Validation scripts must be deterministic and scoped to supported surfaces, not every experiment still present in the repository.
- Release scripts must point at active release artifacts only; retired release notes and release history belong in `docs/archive/`.
- Legacy scripts stay callable only by explicit path and are excluded from canonical docs and the main CI workflow.
