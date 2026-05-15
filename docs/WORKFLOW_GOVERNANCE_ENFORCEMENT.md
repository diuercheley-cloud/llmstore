# Workflow Governance Enforcement

Phase 56 extends deterministic workflows with persistent policy enforcement, immutable governance records, replay governance and stage-level approval chains.

## Core additions

- `CommercialWorkflowPolicyBinding`: persistent stage-to-policy binding.
- `CommercialWorkflowPolicySnapshot`: immutable runtime snapshot of the bound policy and runtime context.
- `CommercialWorkflowApproval`: append-only approval chain events with TTL, delegation and emergency override markers.
- `CommercialWorkflowGovernanceEvent`: immutable governance ledger with chained hashes.
- `CommercialWorkflowReplaySession`: tenant-scoped replay governance session with signed replay reports.

## Policy enforcement modes

- `dry_run`: policy is bound and signed, but execution continues with `policy_gate_status=report_only`.
- `report_only`: same execution behavior as dry run, but intended for governed observation.
- `enforce`: active policy gates the stage. Missing valid policy is denied by default.

## Approval lifecycle

1. Stage binding creates a persistent policy binding and runtime snapshot.
2. If `approval_required` is active, approval requests are persisted per step in an immutable chain.
3. Decisions are appended as new approval events, never replacing the chain history.
4. Expired pending approvals are marked `expired`.
5. Emergency override is supported but must be explicitly flagged and is logged in the governance ledger.

## Replay governance

- Replay sessions are tenant-scoped.
- Cross-tenant replay is rejected.
- Replay reports compare stage drift plus policy snapshot mismatch.
- Signed replay reports are stored on `CommercialWorkflowReplaySession`.
- Replay is considered materially drifted when stage mismatches occur, not merely because execution-local checkpoint hashes differ.

## Drift handling

- Runtime drift is detected by comparing the current runtime context hash against the immutable policy snapshot runtime hash.
- Drift creates a `drift_detected` governance event.
- Snapshot hashes are exposed by admin and portal endpoints for audit.

## Rollback semantics

- Workflow checkpoint rollback still rewinds execution state.
- Phase 56 adds policy rollback recording at stage scope.
- A rollback creates a new `CommercialWorkflowPolicyBinding` pointing to `rollback_from_binding_id`.
- The governance ledger records `workflow_rolled_back`.

## Security model

- Actor metadata is sanitized before persistence.
- Prompt/response/plaintext-like fields are redacted before workflow governance persistence.
- No SaaS dependency is required.
- Offline and airgap compatibility is preserved.

## API surface

- Admin:
  - `/admin/workflows/governance/*`
  - `/admin/workflows/approvals/*`
  - `/admin/workflows/replay-sessions/*`
- Portal:
  - `/portal/workflows/governance/*`
  - `/portal/workflows/replay/*`

## Migration compatibility

- Migration file: `control_plane/alembic/versions/20260515_phase56_workflow_policy_enforcement.py`
- Uses helper fallback for `UUID` and `JSON/JSONB` by dialect.
- Keeps existing workflow tables and only extends them with nullable columns plus new related tables.
- Includes tenant-scoped indexes for governance browsing in SQLite and PostgreSQL.
