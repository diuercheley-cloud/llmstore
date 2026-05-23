# Platform GA Readiness Framework

This framework is the canonical GA gate for `v2.0.1-agentic-operational-maturity`.

## Maturity Levels
- **EXPERIMENTAL**: 0-3 criteria passed.
- **BETA**: 4-7 criteria passed.
- **PILOT_READY**: 8-10 criteria passed.
- **PRODUCTION_READY**: 11/12 criteria passed.
- **GA_READY**: 12/12 criteria passed. GA does not pass with any missing criterion.

## Canonical GA Criteria
The platform is only `GA_READY` when all 12 criteria pass:

1. `operational_readiness_passed`
2. `agentic_readiness_passed`
3. `release_gate_passed`
4. `platform_freeze_passed`
5. `surface_audit_clean`
6. `no_orphaned_flags`
7. `security_warnings_classified`
8. `eval_gate_enforced`
9. `provider_validation_recent`
10. `no_silent_mock_in_production`
11. `no_silent_task_simulation`
12. `tenant_isolation_validated`

## GA Blocking Rules
- A dirty surface audit blocks GA.
- Provider validation must include recent real provider or validated gateway evidence. Mock-only validation does not count.
- Silent mock execution paths do not count as production-safe and block GA.
- Silent task simulation paths in production code block GA.
- Release gates must pass before GA can pass.

## Evidence Sources
- `artifacts/operational-readiness/latest/summary.md`
- `artifacts/agentic-readiness/latest/summary.md`
- `artifacts/releases/v2.0.1-agentic-operational-maturity/summary.md`
- `artifacts/evals/real-provider-validation/latest/results.json`
- `config/feature-flags.yaml`
- `config/security-warning-allowlist.yaml`
- `control_plane/app/services/agents/task_engine.py`

## Artifact Generation
Run:

```bash
scripts/ga-readiness.sh
```

The script writes:
- `artifacts/platform/ga-readiness.md`
- `artifacts/releases/<tag>/ga-readiness.md`

It exits non-zero unless all 12 criteria pass.
