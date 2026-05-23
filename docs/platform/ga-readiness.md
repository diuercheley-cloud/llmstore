# Platform GA Readiness Framework

This framework is the canonical objective maturity model for `v2.0.1-agentic-operational-maturity`.

## Overview
The GA (General Availability) Readiness Framework provides an objective measurement of the operational maturity of the Agentic AI Platform. It evaluates various subsystems—such as metrics, evaluation frameworks, security checks, and platform stability—to ensure the system is truly production-ready before GA launch.

## Maturity Levels
The platform is categorized into one of the following maturity levels based on an accumulated score:

- **EXPERIMENTAL**: Initial development, lacking significant operational guardrails (Score: 0-3).
- **BETA**: Core functionality works, but misses several operational requirements (Score: 4-7).
- **PILOT READY**: Suitable for limited, controlled pilot programs (Score: 8-10).
- **PRODUCTION READY**: Missing minor requirements, but safe for internal production (Score: 11).
- **GA READY**: Fully mature, robust, and operationally excellent for public release (Score: 12).

## Evaluation Criteria
The total score is a composite of 12 distinct checks:
1. `readiness_passing`: Base cluster and service readiness checks pass.
2. `release_gate_passing`: Standard release pipeline gates pass.
3. `no_orphaned_flags`: Codebase has no stale feature flags.
4. `no_orphaned_apis`: Platform does not expose deprecated APIs.
5. `eval_pass_rate_threshold`: Evaluation pass rate > 95%.
6. `slo_stability_required`: Stable performance within SLO margins over a time window.
7. `incident_recovery_tested`: Failsafe mechanisms and rollback playbooks tested.
8. `operational_playbooks_present`: Operations documentation exists.
9. `observability_dashboards_provisioned`: Dashboards are populated.
10. `promotion_gates_enabled`: Automated environment promotion gates are enforced.
11. `security_warnings_classified`: No unacknowledged security warnings.
12. `tenant_isolation_validated`: Strong data and execution isolation between tenants.

## Evidence Sources
- `artifacts/operational-readiness/latest/summary.md`
- `artifacts/releases/<tag>/summary.md`
- `artifacts/evals/real-provider-validation.md`
- `config/feature-flags.yaml`
- `config/security-warning-allowlist.yaml`
- rollout playbooks under `docs/operations/`

## Endpoints
- `GET /admin/platform/ga-readiness`: Returns current score, level, and evaluated state.
- `GET /admin/platform/maturity-report`: Generates and returns a markdown artifact report.
