from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.commercial_workflows import (
    CommercialWorkflowApproval,
    CommercialWorkflowExecution,
    CommercialWorkflowPolicySnapshot,
    CommercialWorkflowStage,
)
from app.services.workflows.workflow_governance_ledger import WorkflowGovernanceLedgerService, sign_governance_payload
from app.services.workflows.workflow_provenance import redact_sensitive_payload, sha256_hex


class WorkflowApprovalChainService:
    def __init__(self) -> None:
        self.ledger = WorkflowGovernanceLedgerService()

    async def _last_chain_event(self, db: AsyncSession, *, chain_id: str) -> CommercialWorkflowApproval | None:
        return (
            await db.execute(
                select(CommercialWorkflowApproval)
                .where(CommercialWorkflowApproval.chain_id == chain_id)
                .order_by(desc(CommercialWorkflowApproval.created_at), desc(CommercialWorkflowApproval.step_index))
                .limit(1)
            )
        ).scalar_one_or_none()

    async def request_approval(
        self,
        db: AsyncSession,
        *,
        execution: CommercialWorkflowExecution,
        stage: CommercialWorkflowStage,
        snapshot: CommercialWorkflowPolicySnapshot | None,
        requested_by: str,
        approvers: list[str],
        ttl_seconds: int = 3600,
        delegated_approvers: list[str] | None = None,
        replay_safe: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> list[CommercialWorkflowApproval]:
        chain_id = sha256_hex(f"{execution.id}:{stage.id}:{requested_by}:{len(approvers)}")[:48]
        existing = (
            await db.execute(
                select(CommercialWorkflowApproval)
                .where(
                    CommercialWorkflowApproval.execution_id == execution.id,
                    CommercialWorkflowApproval.stage_id == stage.id,
                    CommercialWorkflowApproval.chain_id == chain_id,
                    CommercialWorkflowApproval.event_type == "approval_requested",
                )
                .order_by(CommercialWorkflowApproval.step_index.asc())
            )
        ).scalars().all()
        if existing:
            return existing
        expires_at = utc_now() + timedelta(seconds=max(1, ttl_seconds))
        rows: list[CommercialWorkflowApproval] = []
        previous_decision_hash = None
        for step_index, approver in enumerate(approvers):
            delegated = approver in set(delegated_approvers or [])
            decision_payload = {
                "chain_id": chain_id,
                "stage_id": str(stage.id),
                "step_index": step_index,
                "approver": approver,
                "requested_by": requested_by,
                "expires_at": expires_at.isoformat(),
                "delegated": delegated,
                "metadata": redact_sensitive_payload(metadata or {}),
            }
            decision_hash = sha256_hex(decision_payload)
            row = CommercialWorkflowApproval(
                execution_id=execution.id,
                stage_id=stage.id,
                tenant_id=execution.tenant_id,
                snapshot_id=snapshot.id if snapshot else None,
                chain_id=chain_id,
                event_type="approval_requested",
                status="pending",
                step_index=step_index,
                requested_by=requested_by,
                approver=approver,
                delegated_by=requested_by if delegated else None,
                expires_at=expires_at,
                replay_safe=replay_safe,
                previous_decision_hash=previous_decision_hash,
                decision_hash=decision_hash,
                detached_signature=sign_governance_payload(decision_payload, scope="workflow_approval_request"),
                signature_algorithm="ed25519",
                metadata_json=redact_sensitive_payload(metadata or {}),
            )
            db.add(row)
            rows.append(row)
            previous_decision_hash = decision_hash
        stage.approval_required = True
        stage.approval_status = "pending"
        await db.flush()
        await self.ledger.append_event(
            db,
            execution=execution,
            stage_id=stage.id,
            event_type="approval_requested",
            actor_id=requested_by,
            actor_metadata={"chain_id": chain_id},
            event_summary=f"Approval requested for stage {stage.stage_key}",
            event_payload={"chain_id": chain_id, "approver_count": len(approvers), "expires_at": expires_at.isoformat()},
        )
        return rows

    async def expire_pending_approvals(
        self,
        db: AsyncSession,
        *,
        execution_id=None,
    ) -> int:
        stmt = select(CommercialWorkflowApproval).where(
            CommercialWorkflowApproval.status == "pending",
            CommercialWorkflowApproval.expires_at.is_not(None),
        )
        if execution_id is not None:
            stmt = stmt.where(CommercialWorkflowApproval.execution_id == execution_id)
        rows = (await db.execute(stmt)).scalars().all()
        now = utc_now()
        expired = 0
        for row in rows:
            if row.expires_at and row.expires_at <= now:
                row.status = "expired"
                row.expired_at = now
                expired += 1
        await db.flush()
        return expired

    async def record_decision(
        self,
        db: AsyncSession,
        *,
        execution: CommercialWorkflowExecution,
        stage: CommercialWorkflowStage,
        chain_id: str,
        approver: str,
        status: str,
        notes: str | None = None,
        emergency_override: bool = False,
        actor_metadata: dict[str, Any] | None = None,
    ) -> CommercialWorkflowApproval:
        if status not in {"approved", "rejected"}:
            raise ValueError("approval_status_invalid")
        pending = (
            await db.execute(
                select(CommercialWorkflowApproval)
                .where(
                    CommercialWorkflowApproval.chain_id == chain_id,
                    CommercialWorkflowApproval.approver == approver,
                    CommercialWorkflowApproval.status == "pending",
                )
                .order_by(CommercialWorkflowApproval.step_index.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if pending is None:
            raise ValueError("approval_pending_step_not_found")
        if pending.expires_at and pending.expires_at <= utc_now():
            pending.status = "expired"
            pending.expired_at = utc_now()
            raise ValueError("approval_expired")
        last = await self._last_chain_event(db, chain_id=chain_id)
        decision_payload = {
            "chain_id": chain_id,
            "approver": approver,
            "status": status,
            "notes": notes,
            "emergency_override": emergency_override,
            "previous_decision_hash": last.decision_hash if last else None,
        }
        decision = CommercialWorkflowApproval(
            execution_id=execution.id,
            stage_id=stage.id,
            tenant_id=execution.tenant_id,
            snapshot_id=pending.snapshot_id,
            chain_id=chain_id,
            event_type="approval_granted" if status == "approved" else "approval_rejected",
            status=status,
            step_index=pending.step_index,
            requested_by=pending.requested_by,
            approver=approver,
            delegated_by=pending.delegated_by,
            decision_notes=notes,
            expires_at=pending.expires_at,
            emergency_override=emergency_override,
            replay_safe=pending.replay_safe,
            previous_decision_hash=last.decision_hash if last else None,
            decision_hash=sha256_hex(decision_payload),
            detached_signature=sign_governance_payload(decision_payload, scope="workflow_approval_decision"),
            signature_algorithm="ed25519",
            metadata_json=redact_sensitive_payload(actor_metadata or {}),
        )
        db.add(decision)
        pending.status = status
        await db.flush()
        chain_rows = (
            await db.execute(
                select(CommercialWorkflowApproval)
                .where(
                    CommercialWorkflowApproval.chain_id == chain_id,
                    CommercialWorkflowApproval.event_type == "approval_requested",
                )
                .order_by(CommercialWorkflowApproval.step_index.asc())
            )
        ).scalars().all()
        granted = [row for row in chain_rows if row.status == "approved"]
        rejected = [row for row in chain_rows if row.status == "rejected"]
        if rejected:
            stage.approval_status = "rejected"
        elif len(granted) >= len(chain_rows):
            stage.approval_status = "approved"
        else:
            stage.approval_status = "pending"
        await self.ledger.append_event(
            db,
            execution=execution,
            stage_id=stage.id,
            event_type=decision.event_type,
            actor_id=approver,
            actor_metadata=actor_metadata,
            event_summary=f"Approval {status} for stage {stage.stage_key}",
            event_payload={"chain_id": chain_id, "status": status, "step_index": pending.step_index},
        )
        return decision

    async def summarize_chain(
        self,
        db: AsyncSession,
        *,
        chain_id: str,
    ) -> dict[str, Any]:
        rows = (
            await db.execute(
                select(CommercialWorkflowApproval)
                .where(CommercialWorkflowApproval.chain_id == chain_id)
                .order_by(CommercialWorkflowApproval.created_at.asc(), CommercialWorkflowApproval.step_index.asc())
            )
        ).scalars().all()
        return {
            "chain_id": chain_id,
            "items": [
                {
                    "id": str(row.id),
                    "event_type": row.event_type,
                    "status": row.status,
                    "step_index": row.step_index,
                    "requested_by": row.requested_by,
                    "approver": row.approver,
                    "delegated_by": row.delegated_by,
                    "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                    "emergency_override": row.emergency_override,
                    "replay_safe": row.replay_safe,
                    "decision_hash": row.decision_hash,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ],
        }
