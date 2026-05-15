from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.commercial_workflows import (
    CommercialWorkflowExecution,
    CommercialWorkflowPolicySnapshot,
    CommercialWorkflowReplaySession,
)
from app.services.workflows.workflow_governance_ledger import WorkflowGovernanceLedgerService, sign_governance_payload
from app.services.workflows.workflow_provenance import WorkflowProvenanceService, sha256_hex


class WorkflowReplaySessionService:
    def __init__(self) -> None:
        self.provenance = WorkflowProvenanceService()
        self.ledger = WorkflowGovernanceLedgerService()

    async def create_session(
        self,
        db: AsyncSession,
        *,
        original_execution: CommercialWorkflowExecution,
        requested_by: str,
        tenant_id: str | None,
        replay_execution: CommercialWorkflowExecution | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> CommercialWorkflowReplaySession:
        if tenant_id and original_execution.tenant_id and tenant_id != original_execution.tenant_id:
            raise ValueError("cross_tenant_replay_denied")
        if replay_execution is not None and original_execution.tenant_id != replay_execution.tenant_id:
            raise ValueError("cross_tenant_replay_denied")
        provenance = await self.provenance.build_execution_provenance(db, original_execution)
        row = CommercialWorkflowReplaySession(
            original_execution_id=original_execution.id,
            replay_execution_id=replay_execution.id if replay_execution else None,
            tenant_id=original_execution.tenant_id,
            session_status="running",
            requested_by=requested_by,
            deterministic_snapshot_hash=provenance["provenance_hash"],
            metadata_json=metadata_json or {},
        )
        db.add(row)
        original_execution.replay_status = "running"
        await db.flush()
        await self.ledger.append_event(
            db,
            execution=original_execution,
            replay_session_id=row.id,
            event_type="replay_started",
            actor_id=requested_by,
            actor_metadata={"tenant_id": tenant_id},
            event_summary=f"Replay session started for execution {original_execution.id}",
            event_payload={"replay_session_id": str(row.id), "replay_execution_id": str(replay_execution.id) if replay_execution else None},
        )
        return row

    async def complete_session(
        self,
        db: AsyncSession,
        *,
        session_row: CommercialWorkflowReplaySession,
    ) -> CommercialWorkflowReplaySession:
        original = await db.get(CommercialWorkflowExecution, session_row.original_execution_id)
        if original is None:
            raise ValueError("workflow_execution_not_found")
        replay = await db.get(CommercialWorkflowExecution, session_row.replay_execution_id) if session_row.replay_execution_id else None
        drift = (
            await self.provenance.detect_pipeline_drift(db, original.id, replay.id)
            if replay is not None
            else {
                "drift_detected": False,
                "mismatches": [],
                "original_execution_hash_chain": original.execution_hash_chain,
                "replay_execution_hash_chain": None,
                "original_ledger_hash": original.ledger_hash,
                "replay_ledger_hash": None,
            }
        )
        original_snapshots = (
            await db.execute(
                select(CommercialWorkflowPolicySnapshot).where(CommercialWorkflowPolicySnapshot.execution_id == original.id)
            )
        ).scalars().all()
        replay_snapshots = (
            await db.execute(
                select(CommercialWorkflowPolicySnapshot).where(CommercialWorkflowPolicySnapshot.execution_id == replay.id)
            )
        ).scalars().all() if replay is not None else []
        original_policy_hashes = [row.snapshot_hash for row in original_snapshots]
        replay_policy_hashes = [row.snapshot_hash for row in replay_snapshots]
        policy_mismatch = original_policy_hashes != replay_policy_hashes
        report = {
            "original_execution_id": str(original.id),
            "replay_execution_id": str(replay.id) if replay else None,
            "drift": drift,
            "policy_snapshot_hashes": {
                "original": original_policy_hashes,
                "replay": replay_policy_hashes,
            },
            "policy_mismatch_detected": policy_mismatch,
        }
        comparison_hash = sha256_hex(report)
        material_drift = bool(drift.get("mismatches"))
        session_row.session_status = "completed" if not material_drift and not policy_mismatch else "drift_detected"
        session_row.comparison_hash = comparison_hash
        session_row.report_hash = sha256_hex({"comparison_hash": comparison_hash, "completed_at": utc_now().isoformat()})
        session_row.report_signature = sign_governance_payload(report, scope="workflow_replay_report")
        session_row.mismatch_detected = material_drift
        session_row.policy_mismatch_detected = policy_mismatch
        session_row.drift_score = round(1.0 if material_drift or policy_mismatch else 0.0, 4)
        session_row.replay_report_json = report
        session_row.completed_at = utc_now()
        original.replay_status = session_row.session_status
        await db.flush()
        await self.ledger.append_event(
            db,
            execution=original,
            replay_session_id=session_row.id,
            event_type="replay_completed",
            actor_id=session_row.requested_by,
            actor_metadata={"policy_mismatch": policy_mismatch},
            event_summary=f"Replay session completed for execution {original.id}",
            event_payload={"replay_session_id": str(session_row.id), "comparison_hash": comparison_hash},
        )
        return session_row
