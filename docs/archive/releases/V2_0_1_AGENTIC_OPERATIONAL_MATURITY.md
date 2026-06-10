---
owner: platform-ops
status: consolidated
---

# v2.0.1 Agentic Operational Maturity

`v2.0.1-agentic-operational-maturity` consolidates the `v2.0.0` agentic platform into an operator-ready release line. The focus shifts from proving architectural capability to proving operational discipline: controlled activation, explicit rollout modes, objective GA scoring, surface reduction, feature-flag cleanup, security warning governance, and reproducible release evidence.

## Scope

1. Deployment modes
2. Feature flag cleanup
3. Security warning cleanup
4. Surface reduction
5. Runtime activation playbooks
6. Real provider validation
7. GA readiness framework

## Release posture

- `appliance` remains the default-safe posture and keeps the agentic runtime disabled.
- `pilot` is the official activation mode for governed read-only rollout with strict approvals and budgets.
- `production` is the official activation mode for eval-gated, SLO-enforced runtime execution.
- `enterprise_managed` is the federated posture with managed control-plane and strict tenant isolation.

## Operational criteria

- No critical orphaned feature flags.
- No relevant uncleared security warnings.
- Runtime activation is documented and executable through official playbooks.
- GA classification is objective and reproducible from repository evidence and generated artifacts.
- Surface reduction is complete: 242 previously unreferenced agentic registry endpoints have been classified and unreferenced registry count is exactly 0.
- Release evidence is written under `artifacts/releases/v2.0.1-agentic-operational-maturity/`.

## Required validation commands

```bash
make test
make validate-quick
make security
make operational-readiness
make agentic-readiness
make feature-flag-audit
make platform-freeze-check
make complexity-report
make release-gate TAG=v2.0.1-agentic-operational-maturity
```

## Evidence set

- `summary.md`
- `validation.md`
- `ga-readiness.md`
- `feature-flags.md`
- `surface-audit.md`
- `security-cleanup.md`

## Expected outcome

This release is successful only if the platform can be described as operationally mature: safe to activate through governed playbooks, auditable through objective artifacts, and classified with a clear GA readiness score.
