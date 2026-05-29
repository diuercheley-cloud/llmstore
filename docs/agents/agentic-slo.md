---
owner: platform-ops
status: consolidated
---

# Agentic Service Level Objectives (SLOs)

## Critical SLOs

| Objective | Target | Measurement |
| :--- | :--- | :--- |
| Success Rate | 98% | `count(run.completed) / count(run.total)` |
| Execution Latency | < 120s | p95 of `run_duration_seconds` |
| Security Compliance | 100% | `count(policy.denied_violation) == 0` |

## Reporting

SLOs are calculated per agent and environment. Detailed reports are available via the Admin Dashboard.
