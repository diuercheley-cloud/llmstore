from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.core.time import utc_now
from app.models.commercial_autonomous_guardrails import (
    CommercialAutonomousExecutionPolicy,
    CommercialHumanApprovalCheckpoint,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .blast_radius_analysis import sha256_hex


class HumanCheckpointingService:
    def _checkpoint_hash(self, payload: dict[str, Any]) -> str:
        return sha256_hex(payload)

    async def create_checkpoints(
        self,
        db: AsyncSession,
        *,
        policy: CommercialAutonomousExecutionPolicy | None,
        request: dict[str, Any],
        approval_chain_id=None,
        persist: bool = True,
    ) -> list[CommercialHumanApprovalCheckpoint]:
        sanitized = sanitize_report_payload(request)
        stage_defs = (policy.approval_stages_json if policy and policy.approval_stages_json else None) or [
            {"stage": 1, "required_approvals": 1}
        ]
        checkpoints: list[CommercialHumanApprovalCheckpoint] = []
        for stage_def in stage_defs:
            stage = int(stage_def.get("stage") or stage_def.get("checkpoint_stage") or 1)
            required = int(stage_def.get("required_approvals") or stage_def.get("approver_count") or 1)
            checkpoint = CommercialHumanApprovalCheckpoint(
                policy_id=policy.id if policy else None,
                approval_chain_id=approval_chain_id,
                tenant_id=sanitized.get("tenant_id"),
                action_type=str(sanitized.get("action_type") or "unknown"),
                target_type=str(sanitized.get("target_type") or "unknown"),
                target_id=sanitized.get("target_id"),
                checkpoint_stage=stage,
                required_approvals=required,
                approvals_json=[],
                rejections_json=[],
                status="pending",
                expires_at=utc_now() + timedelta(hours=24),
                immutable_hash=self._checkpoint_hash(
                    {
                        "action_type": sanitized.get("action_type"),
                        "checkpoint_stage": stage,
                        "required_approvals": required,
                        "target_id": sanitized.get("target_id"),
                        "tenant_id": sanitized.get("tenant_id"),
                    }
                ),
                metadata_json={"request": sanitized, "stage_definition": stage_def},
            )
            db.add(checkpoint)
            checkpoints.append(checkpoint)
        if persist:
            await db.commit()
            for item in checkpoints:
                await db.refresh(item)
        else:
            await db.flush()
        return checkpoints

    async def approve_checkpoint(
        self,
        db: AsyncSession,
        *,
        checkpoint_id,
        approver: str,
        notes: str | None = None,
        segregated_from: str | None = None,
    ) -> CommercialHumanApprovalCheckpoint:
        checkpoint = await db.get(CommercialHumanApprovalCheckpoint, checkpoint_id)
        if checkpoint is None:
            raise ValueError("checkpoint_not_found")
        if checkpoint.status == "rejected":
            raise ValueError("checkpoint_rejected")
        approvals = list(checkpoint.approvals_json or [])
        if approver not in {item.get("approver") for item in approvals}:
            approvals.append(
                {
                    "approver": approver,
                    "notes": notes,
                    "segregated_from": segregated_from,
                    "approved_at": utc_now().isoformat(),
                }
            )
        checkpoint.approvals_json = approvals
        checkpoint.status = "approved" if len(approvals) >= checkpoint.required_approvals else "pending"
        checkpoint.decided_at = utc_now() if checkpoint.status == "approved" else None
        await db.commit()
        await db.refresh(checkpoint)
        return checkpoint

    async def reject_checkpoint(
        self,
        db: AsyncSession,
        *,
        checkpoint_id,
        approver: str,
        reason: str,
    ) -> CommercialHumanApprovalCheckpoint:
        checkpoint = await db.get(CommercialHumanApprovalCheckpoint, checkpoint_id)
        if checkpoint is None:
            raise ValueError("checkpoint_not_found")
        rejections = list(checkpoint.rejections_json or [])
        rejections.append({"approver": approver, "reason": reason, "rejected_at": utc_now().isoformat()})
        checkpoint.rejections_json = rejections
        checkpoint.status = "rejected"
        checkpoint.decided_at = utc_now()
        await db.commit()
        await db.refresh(checkpoint)
        return checkpoint

    async def validate_chain(
        self,
        db: AsyncSession,
        *,
        policy_id=None,
        target_type: str,
        target_id: str | None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        stmt = select(CommercialHumanApprovalCheckpoint).where(
            CommercialHumanApprovalCheckpoint.target_type == target_type,
            CommercialHumanApprovalCheckpoint.target_id == target_id,
        )
        if policy_id is not None:
            stmt = stmt.where(CommercialHumanApprovalCheckpoint.policy_id == policy_id)
        if tenant_id is not None:
            stmt = stmt.where(CommercialHumanApprovalCheckpoint.tenant_id == tenant_id)
        rows = (await db.execute(stmt)).scalars().all()
        rows = sorted(rows, key=lambda item: item.checkpoint_stage)
        if not rows:
            return {"approved": False, "reason": "missing_checkpoint_chain", "checkpoints": []}
        approved = all(item.status == "approved" for item in rows)
        return {
            "approved": approved,
            "reason": None if approved else "checkpoint_pending",
            "checkpoints": rows,
            "approval_hash": sha256_hex(
                [
                    {
                        "checkpoint_id": str(item.id),
                        "stage": item.checkpoint_stage,
                        "status": item.status,
                        "approvals": item.approvals_json,
                    }
                    for item in rows
                ]
            ),
        }
