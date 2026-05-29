# v2.x-agentic-consolidation-hardening

Date: 2026-05-28

## Goal

Promote the agentic line from broad experimental surface area to operationally hardened release posture.

## Scope

- Reduce dead surface and archive deprecated release-era scripts.
- Promote critical capabilities with deterministic gates and controlled production profile validation.
- Replace simulated critical checks with hermetic or fail-closed validation paths.
- Harden multi-agent promotion, rollback, and specialist-routing controls.
- Close core-service coverage gaps for the services introduced in this release delta.
- Align supported-surface, freeze rules, and documentation checks with the actual release scope.

## Release Criteria

- Fewer orphan flags and less dead operational surface.
- Deterministic `agentic-production` profile validation.
- Core changed services covered by tests.
- Freeze, readiness, security, and complexity gates green.
- Consistent docs and release artifacts.

## Validation

- `make test`
- `make validate-quick`
- `make security`
- `make operational-readiness`
- `make agentic-readiness`
- `make real-execution-readiness`
- `make feature-flag-audit`
- `make service-coverage-gate`
- `make platform-freeze-check`
- `make complexity-report`
- `bash scripts/check-secrets.sh --all`
- `scripts/check-alembic-integrity.sh`

## Working Tree Governance

This release introduces formal working tree governance to prevent future releases from being "green but dirty."

### Classification Categories

Every file in the working tree is explicitly classified as one of:
- `release_artifact` — committed as part of this release
- `generated_runtime` — tracked in `artifacts/`, governed by policy
- `temporary_file` — deleted during reconciliation
- `valid_uncommitted_fix` — committed as feature/deprecation work
- `should_commit` — staged and committed
- `should_delete` — removed during cleanup
- `should_ignore` — added to `.gitignore` if persistent

### Local Drift Policy

- **dirty_allowed_runtime**: Only explicit runtime artifacts under `artifacts/`. Release may proceed.
- **dirty_blocking**: Forbidden debug files, unclassified files, or secrets detected. Release BLOCKED.
- **clean**: Perfectly clean working tree.
- **clean_with_allowed_local**: Clean except for explicitly allowed local env files (`.env.local`, etc.).

### Runtime Artifact Policy

- Allowed: `artifacts/releases/*`, `artifacts/runtime/*`, `artifacts/platform/*`
- Forbidden: `*.pyc`, `__pycache__/`, `.pytest_cache/`, `*.db`, `*.gguf`, `*.log`, `core.*`, `*.dump`
- Debug leftovers are always blocking.
- Secrets in untracked files are always blocking.

### Release Reproducibility

- Git SHA `0b207e2` is the base for v2.x-agentic-consolidation-hardening.
- Release manifest (`release-manifest.json`) captures enabled flags, API surface, supported surface, migrations, deps, and runtime providers.
- Working tree certification (`make working-tree-certification TAG=v2.x-agentic-consolidation-hardening`) validates the tree is `clean` or `clean_with_allowed_local` before finalization.

## Reconcile Working Tree

```bash
make working-tree-certification TAG=v2.x-agentic-consolidation-hardening
bash scripts/reconcile-working-tree.sh v2.x-agentic-consolidation-hardening
git commit -m "release(v2.x-agentic-consolidation-hardening): working-tree reconciliation and governance hardening"
git tag -a v2.x-agentic-consolidation-hardening -m "Release v2.x-agentic-consolidation-hardening"
```

## Notes

- `agentic-readiness` is allowed to pass in `disabled` state because runtime opt-in remains the safe default.
- Live `agentic-production` validation falls back to deterministic offline checks when the target deployment does not yet expose the current readiness router.
