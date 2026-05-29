---
owner: platform-ops
status: consolidated
---

# Commercial Infrastructure Simulation & Safety Gates (Phase 21.1)

This module provides a simulation and protection layer for all infrastructure-impacting actions. Before any scaling, rerouting, or failover occurs, it must pass through a simulation and be validated against safety policies.

## Key Components

### 1. Simulation Engine
Located in `control_plane/app/services/routing/commercial_infra_simulation.py`, this service estimates the impact of requested actions on:
- **Cost**: Predicted increase in BRL/hour.
- **Margin**: Predicted impact on profitability.
- **SLA**: Predicted change in SLA violation risk.
- **Capacity**: Predicted RPM/concurrency changes.
- **Blast Radius**: Classification of how much of the infrastructure is affected (Low, Medium, High, Critical).

### 2. Safety Gates
Located in `control_plane/app/services/routing/commercial_safety_gates.py`, this service validates simulations against `CommercialSafetyPolicy` rules.
- **Blocked**: Actions that exceed cost/risk limits are automatically blocked.
- **Requires Approval**: High-risk actions (e.g., Cluster Failover, High Blast Radius) are marked for manual review.
- **Allowed**: Safe actions that fall within policy boundaries.

### 3. Approval Workflow
All high-risk actions are registered as `CommercialApprovalRecord`. In this phase, it only tracks the status (pending, approved, rejected). Future phases will integrate with execution adapters.

## Configuration

New environment variables:
- `COMMERCIAL_INFRA_SIMULATION_ENABLED`: Master switch for simulation layer.
- `COMMERCIAL_INFRA_EXECUTION_MODE`: `simulation_only` (current), `approval_required`, `execute_opt_in_future`.
- `COMMERCIAL_SAFETY_GATES_ENABLED`: Enable/disable policy validation.
- `COMMERCIAL_MAX_BLAST_RADIUS`: Default limit for automated actions.
- `COMMERCIAL_MAX_AUTOSCALING_COST_INCREASE_PERCENT`: Safety threshold for cost.

## API Endpoints

- `GET /admin/routing/infra/simulations`: List recent simulations.
- `POST /admin/routing/infra/simulate`: Manually trigger a simulation.
- `GET /admin/routing/infra/safety-policies`: List active safety policies.
- `POST /admin/routing/infra/approvals`: Record an approval decision.

## Blast Radius Logic

- **Low**: Small changes (e.g., +1 node) in a single cluster.
- **Medium**: Significant changes (e.g., +5 nodes) or tier-wide throttling.
- **High**: Large scale changes (+10 nodes) or provider-wide routing shifts.
- **Critical**: Cluster failover, cross-region routing, or mass scaling (>20 nodes).

## Testing

Run tests:
```bash
pytest tests/test_commercial_infra_simulation.py
```

Run validation script:
```bash
make validate-commercial-infra-simulation
```
