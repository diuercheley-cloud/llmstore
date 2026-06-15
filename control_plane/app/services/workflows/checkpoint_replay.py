from __future__ import annotations

from typing import Any

from app.core.time import utc_now
from app.models.commercial.commercial_workflows import (
    CommercialWorkflowCheckpoint,
    CommercialWorkflowExecution,
    CommercialWorkflowStage,
)
from app.services.workflows.workflow_governance_ledger import WorkflowGovernanceLedgerService
from app.services.workflows.workflow_policy_enforcement import WorkflowPolicyEnforcementService
from app.services.workflows.workflow_provenance import canonical_json, sha256_hex
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession


def _checkpoint_signature(checkpoint_hash: str, algorithm: str = "ed25519") -> str:
    return (
        f"{algorithm}:{sha256_hex({'checkpoint_hash': checkpoint_hash, 'scope': 'workflow'})[:48]}"
    )


class WorkflowCheckpointReplayService:
    def __init__(self) -> None:
        self.policy_enforcement = WorkflowPolicyEnforcementService()
        self.ledger = WorkflowGovernanceLedgerService()

    async def create_checkpoint(
        self,
        db: AsyncSession,
        *,
        execution: CommercialWorkflowExecution,
        stage: CommercialWorkflowStage | None,
        step_index: int,
        input_hash: str | None,
        output_hash: str | None,
        state_snapshot: dict[str, Any] | None,
    ) -> CommercialWorkflowCheckpoint:
        previous = (
            await db.execute(
                select(CommercialWorkflowCheckpoint)
                .where(CommercialWorkflowCheckpoint.execution_id == execution.id)
                .order_by(desc(CommercialWorkflowCheckpoint.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        snapshot_hash = sha256_hex(
            {
                "execution_id": str(execution.id),
                "stage_key": stage.stage_key if stage else None,
                "step_index": step_index,
                "input_hash": input_hash,
                "output_hash": output_hash,
                "state_snapshot": state_snapshot or {},
                "previous_checkpoint_hash": previous.snapshot_hash if previous else None,
            }
        )
        checkpoint = CommercialWorkflowCheckpoint(
            execution_id=execution.id,
            stage_id=stage.id if stage else None,
            step_index=step_index,
            stage_key=stage.stage_key if stage else None,
            step_input_hash=input_hash,
            step_output_hash=output_hash,
            snapshot_hash=snapshot_hash,
            previous_checkpoint_hash=previous.snapshot_hash if previous else None,
            state_snapshot=state_snapshot,
            detached_signature=_checkpoint_signature(snapshot_hash),
            signature_algorithm="ed25519",
            immutable_hash=sha256_hex(
                {
                    "snapshot_hash": snapshot_hash,
                    "previous_checkpoint_hash": previous.snapshot_hash if previous else None,
                    "created_at": utc_now().isoformat(),
                }
            ),
            replay_nonce=sha256_hex(
                f"{execution.id}:{stage.stage_key if stage else 'checkpoint'}:{step_index}"
            )[:32],
        )
        db.add(checkpoint)
        await db.flush()
        execution.last_checkpoint_hash = checkpoint.snapshot_hash
        if stage is not None:
            stage.checkpoint_hash = checkpoint.snapshot_hash
        return checkpoint

    async def validate_checkpoint_chain(
        self,
        db: AsyncSession,
        execution_id,
    ) -> dict[str, Any]:
        rows = (
            (
                await db.execute(
                    select(CommercialWorkflowCheckpoint)
                    .where(CommercialWorkflowCheckpoint.execution_id == execution_id)
                    .order_by(
                        CommercialWorkflowCheckpoint.step_index.asc(),
                        CommercialWorkflowCheckpoint.created_at.asc(),
                    )
                )
            )
            .scalars()
            .all()
        )
        issues: list[str] = []
        previous_hash = None
        for row in rows:
            if row.previous_checkpoint_hash != previous_hash:
                issues.append(f"checkpoint_chain_break:{row.stage_key or row.step_index}")
            expected_sig = _checkpoint_signature(row.snapshot_hash or "")
            if row.detached_signature != expected_sig:
                issues.append(f"checkpoint_signature_invalid:{row.stage_key or row.step_index}")
            previous_hash = row.snapshot_hash
        return {"valid": not issues, "issues": issues, "count": len(rows)}

    async def rollback_to_checkpoint(
        self,
        db: AsyncSession,
        *,
        execution: CommercialWorkflowExecution,
        checkpoint_id,
    ) -> dict[str, Any]:
        checkpoint = await db.get(CommercialWorkflowCheckpoint, checkpoint_id)
        if checkpoint is None or checkpoint.execution_id != execution.id:
            raise ValueError("checkpoint_not_found")
        stage_rows = (
            (
                await db.execute(
                    select(CommercialWorkflowStage)
                    .where(CommercialWorkflowStage.execution_id == execution.id)
                    .order_by(CommercialWorkflowStage.stage_order.asc())
                )
            )
            .scalars()
            .all()
        )
        cleared: list[str] = []
        for stage in stage_rows:
            if stage.stage_order > checkpoint.step_index:
                stage.status = "rolled_back"
                stage.input_hash = None
                stage.output_hash = None
                stage.stage_hash = None
                stage.lineage_hash = None
                stage.receipt_hash = None
                stage.checkpoint_hash = None
                stage.executed_at = None
                cleared.append(stage.stage_key)
        execution.status = "paused"
        execution.paused_at = utc_now()
        execution.current_step_index = checkpoint.step_index
        execution.last_checkpoint_hash = checkpoint.snapshot_hash
        rollback_stage = next(
            (row for row in stage_rows if row.stage_order == checkpoint.step_index), None
        )
        if rollback_stage is not None:
            await self.policy_enforcement.rollback_stage_policy(
                db,
                execution=execution,
                stage=rollback_stage,
                actor_id="system",
            )
        await self.ledger.append_event(
            db,
            execution=execution,
            stage_id=rollback_stage.id if rollback_stage else None,
            event_type="workflow_rolled_back",
            actor_id="system",
            actor_metadata={"checkpoint_id": str(checkpoint.id)},
            event_summary=f"Workflow rolled back to checkpoint {checkpoint.id}",
            event_payload={
                "rolled_back_stages": cleared,
                "resume_from_stage_index": checkpoint.step_index,
            },
        )
        return {
            "execution_id": str(execution.id),
            "checkpoint_id": str(checkpoint.id),
            "rolled_back_stages": cleared,
            "resume_from_stage_index": checkpoint.step_index,
        }

    async def export_replay_bundle(
        self,
        db: AsyncSession,
        execution_id,
    ) -> dict[str, Any]:
        execution = await db.get(CommercialWorkflowExecution, execution_id)
        if execution is None:
            raise ValueError("execution_not_found")
        checkpoints = (
            (
                await db.execute(
                    select(CommercialWorkflowCheckpoint)
                    .where(CommercialWorkflowCheckpoint.execution_id == execution_id)
                    .order_by(
                        CommercialWorkflowCheckpoint.step_index.asc(),
                        CommercialWorkflowCheckpoint.created_at.asc(),
                    )
                )
            )
            .scalars()
            .all()
        )
        bundle = {
            "execution_id": str(execution.id),
            "tenant_id": execution.tenant_id,
            "status": execution.status,
            "ledger_hash": execution.ledger_hash,
            "checkpoints": [
                {
                    "stage_key": row.stage_key,
                    "step_index": row.step_index,
                    "snapshot_hash": row.snapshot_hash,
                    "previous_checkpoint_hash": row.previous_checkpoint_hash,
                    "immutable_hash": row.immutable_hash,
                    "detached_signature": row.detached_signature,
                }
                for row in checkpoints
            ],
        }
        bundle["bundle_hash"] = sha256_hex(canonical_json(bundle))
        return bundle
