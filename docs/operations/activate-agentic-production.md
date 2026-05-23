# Production Activation Playbook

This playbook outlines the steps to transition the Agentic Runtime from Pilot to Production mode.

## Objective
To enable full-scale, automated agent operations with strict guardrails, autoscaling, and enforcement of evaluations.

## Prerequisites
- Successful completion of the Pilot phase.
- `AGENTIC_READINESS_STATUS=passed`, `AGENTIC_SLO_STATUS=passed`, and `AGENTIC_BUDGET_STATUS=passed` must be present in the activation env file.

## Execution
Run the production activation script:
```bash
./scripts/activate-agentic-production.sh
```

## State Changes
During execution, the following validation checks are performed:
- Validates Readiness
- Validates SLOs
- Validates Budgets

Upon success, the following changes are made:
- **Deployment mode:** `DEPLOYMENT_MODE=production`
- **Evaluations execution:** `AGENT_EVALS_ENABLED=true`
- **Regression gate:** `AGENT_EVAL_REGRESSION_GATE_ENABLED=true`
- **Worker Autoscaling:** `AGENT_WORKER_AUTOSCALING_ENABLED=true`
- **Promotion Gates:** `AGENT_PROMOTION_REQUIRES_EVALS=true`
