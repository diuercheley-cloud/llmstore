# Release v2.x-agentic-platform-complete-hardening

## Goal

Transform the local/governed core into a more complete agentic platform without overstating production support.

## Scope

- Real distributed-runtime primitives for node registration, heartbeat, placement, lease, and failover.
- Opt-in enterprise multi-cluster and managed control-plane surfaces with metadata-safe boundaries.
- Connector, MCP, and plugin catalog governance with checksum/signature posture.
- Platform profiles replacing unsupported flag combinatorics as the primary operator contract.
- Production-claim hardening: non-mock E2E required before a feature is called production-safe.
- Smaller, more honest supported surface.

## Release Position

- `production_core`: local/governed control plane, agent runtime core, readiness, worker, tool governance, and existing non-mock hardened execution paths.
- `production_optional`: platform profiles and plugin runtime under explicit operator enablement.
- `beta`: distributed runtime, multi-cluster, managed control plane, capability catalog, signed plugin supply chain, and production sandbox hardening.
- `non-production`: any path that still depends on mock-backed E2E or initialization-only evidence.

## Required Validation

```bash
make test
make validate-quick
make security
make operational-readiness
make agentic-readiness
make real-execution-readiness
make production-agentic-e2e
make platform-freeze-check
make feature-flag-audit
make complexity-report
make release-gate TAG=v2.x-agentic-platform-complete-hardening
bash scripts/validators/check-secrets.sh --all
scripts/validators/check-alembic-integrity.sh
```

## Exit Criteria

- Critical placeholders are removed or explicitly marked non-production.
- Production claims require non-mock E2E evidence.
- Distributed runtime exists as real code and governed surface.
- Multi-cluster and managed control plane remain metadata-safe and operationally explicit.
- Sandbox production posture is fail-closed and never silently simulated.
- Supported configuration posture is profile-driven.
- Release artifact pack documents both passes and blockers.
