---
owner: platform-ops
status: consolidated
---

# v2.1.1 Agentic Scale Hardening

## Objective

Harden the platform for enterprise-critical scale without weakening the safe default posture.

## Scope

1. Sandbox MicroVM/gVisor.
2. MCP OAuth Token Exchange.
3. GraphRAG cache + PostgreSQL/pgvector/pgRouting.
4. Auto-Optimizer tournaments.
5. Telemetry leaky-bucket backpressure.

## Default Posture

- Firecracker and gVisor remain disabled by default.
- MCP OAuth token exchange remains disabled by default.
- External Knowledge Graph provider paths remain disabled by default.
- Optimizer winner application remains disabled by default.
- Telemetry backpressure remains enabled by default.

## Release Gates

Run:

```bash
make test
make validate-quick
make security
make operational-readiness
make agentic-readiness
make agent-security-tests
make agent-kg-benchmark
make platform-freeze-check
make complexity-report
make release-gate TAG=v2.1.1-agentic-scale-hardening
bash scripts/check-secrets.sh --all
scripts/check-alembic-integrity.sh
```

## Release Criteria

1. MicroVM and gVisor providers are available as explicit opt-in sandbox providers.
2. MCP can operate with delegated tenant or user identity.
3. GraphRAG supports cache acceleration and a production PostgreSQL provider path.
4. Optimizer tournaments support governed parallel evaluation.
5. Telemetry protects exporter liveness with backpressure.
6. No new critical-scale control is enabled implicitly by default.

## Expected Artifacts

- `artifacts/releases/v2.1.1-agentic-scale-hardening/summary.md`
- `artifacts/releases/v2.1.1-agentic-scale-hardening/validation.md`
- `artifacts/releases/v2.1.1-agentic-scale-hardening/sandbox.md`
- `artifacts/releases/v2.1.1-agentic-scale-hardening/mcp-oauth.md`
- `artifacts/releases/v2.1.1-agentic-scale-hardening/graphrag-performance.md`
- `artifacts/releases/v2.1.1-agentic-scale-hardening/optimizer-tournaments.md`
- `artifacts/releases/v2.1.1-agentic-scale-hardening/telemetry-backpressure.md`
