---
owner: platform-ops
status: consolidated
---

# Operational Remediation Execution

## Introduction
The Remediation Execution system manages the implementation of remediation plans. It ensures that any action taken on the system is authorized, documented, and reversible.

## Surface Status

- `GET /admin/operations/remediation-executions/`: `beta`
- `POST /admin/operations/remediation-executions/prepare`: `beta`
- `POST /admin/operations/remediation-executions/execute`: `simulated`
- `GET /admin/operations/remediation-executions/kill-switch`: `beta`
- `POST /admin/operations/remediation-executions/kill-switch`: `beta`
- `GET /admin/operations/remediation-executions/{execution_id}`: `beta`
- `POST /admin/operations/remediation-executions/{execution_id}/kill`: `beta`
- `GET /admin/operations/remediation-executions/{execution_id}/rollback-plan`: `beta`

## Execution Lifecycle
1. **Preparation:** An execution record is created from a plan. A rollback plan is automatically generated.
2. **Gating:** The system checks for approvals, verifies the kill-switch state, and ensures the rollback plan is ready.
3. **Simulation:** (Phase 72) Steps are processed by the `SimulatedRemediationExecutionAdapter`.
4. **Finalization:** The execution status is updated, and a post-execution receipt is generated.

## Safety Gates

### 1. Approval Gate
For non-dry-run executions, the system requires verified approvals if:
- The risk level is `high` or `critical`.
- The blast radius is `high` or `critical`.
- Any step is marked as `irreversible`.

### 2. Kill-Switch Gate
Every execution checks the client's global kill-switch. If enabled, all remediation executions are immediately blocked. This is used during major outages or maintenance windows where automated planning might be dangerous.

### 3. Rollback Gate
A valid rollback plan must be present before any execution can transition out of the `pending` state for non-dry-run modes.

## Simulation vs. Real Execution
In the current phase, only `simulation` mode is supported.
- **Simulation:** Uses a deterministic adapter to model expected system changes. Safe for production-like testing.
- **Approved Execution:** (Reserved for future phases) Will interface with real infrastructure providers.

`POST /execute` is intentionally classified as `simulated`. The surrounding planning, gating, receipt, rollback-plan, and kill-switch APIs are real control-plane surfaces, but the execution step itself does not reach live infrastructure providers yet.

## Emergency Kill
Operators can manually "kill" an active execution at any time. This halts the sequence and marks the execution as `killed`, preventing further steps from being processed.
