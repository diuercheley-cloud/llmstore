# v2.x-agentic-production-maturity

Date: 2026-05-28

## Goal

Remove the remaining gaps that prevented the stack from being described as a production-grade agentic AI platform without qualification.

## Scope

- Enforce real graph pathfinding and explicit mock posture.
- Enforce real MCP discovery/execution posture with explicit mock-only mode.
- Enforce fail-closed multi-agent arbitration in real mode.
- Eliminate silent eval success paths in production-on validation.
- Validate runtime-on posture through the maintained agentic production-on target.
- Keep supported surface classification honest and aligned with actual runtime flags.
- Certify a clean working tree before the release gate closes.

## Release Criteria

- No flagship path uses silent mock fallback.
- Runtime-on posture is actually validated, not inferred from disabled safe defaults.
- Production-facing surface is classified defensibly.
- Working tree is clean at certification time.
- Release gate is green.

## Validation

- `make test`
- `make validate-quick`
- `make security`
- `make operational-readiness`
- `make agentic-readiness`
- `make agentic-production-on-readiness`
- `make real-execution-readiness`
- `make platform-freeze-check`
- `make feature-flag-audit`
- `make working-tree-certification TAG=v2.x-agentic-production-maturity`
- `make release-gate TAG=v2.x-agentic-production-maturity`
- `bash scripts/check-secrets.sh --all`
- `scripts/check-alembic-integrity.sh`

## Notes

- `agentic-readiness` may still report `disabled` as a safe default; this release requires the separate `agentic-production-on-readiness` target for runtime-on evidence.
- MCP and multi-agent remain opt-in and experimental in supported surface terms, but their enabled paths now fail closed instead of silently degrading.
