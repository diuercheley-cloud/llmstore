# Developer Experience

## Improvements

- Added targeted tests for the new high-priority agentic surfaces.
- Restored feature-flag governance so `make validate-quick` and `make feature-flag-audit` are actionable again.
- Added focused coverage references for changed P0 services, allowing `platform-freeze-check` to certify the current delta.

## Friction Still Present

- The release gate hard-fails on any dirty worktree, which is correct governance but blocks certification while large in-flight changes remain uncommitted.
