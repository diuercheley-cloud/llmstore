---
owner: platform-ops
status: consolidated
---

# Agent Evaluation Gates

## Overview

Evaluation gates are mandatory quality checks that an agent must pass before it can be promoted to production or activated. They ensure that new versions of an agent do not regress in performance, safety, or reliability.

## Feature Flags

- `AGENT_EVALS_ENABLED`: Master switch for the evaluation system.
- `AGENT_PRODUCTION_REQUIRES_EVAL_BASELINE`: If true, an agent cannot be promoted to production without a registered baseline.
- `AGENT_EVAL_REGRESSION_GATE_ENABLED`: If true, the promotion check will compare the candidate run against the baseline and fail if quality has dropped.

## Blockers

A promotion gate will fail if any of the following occur:
1. **Regression**: The pass rate dropped significantly compared to the baseline.
2. **Golden Task Failure**: Any case marked as "golden" failed.
3. **Secret Leak**: A secret marker (e.g., `SECRET_`, `KEY_`) was detected in the agent's output.
4. **Safety Violation**: Prohibited tools were called or cross-tenant access was attempted.
5. **Cost/Latency**: The run exceeded defined cost or latency limits.

## API Usage

### Check Promotion Gate

```bash
POST /admin/agent-evals/promotion-check/{agent_id}
{
  "eval_run_id": "..."
}
```

### Audit Override

In emergencies, an admin can bypass the gate using `audit_override: true` with a mandatory reason.
