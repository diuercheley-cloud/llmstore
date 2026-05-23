# Owner: commercial-ops
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin, get_db
from app.models.commercial_autonomous_guardrails import (
    CommercialAutonomousExecutionReceipt,
    CommercialExecutionBlastRadius,
    CommercialExecutionGuardrailEvent,
    CommercialHumanApprovalCheckpoint,
)
from app.services.governance.autonomous_guardrails import AutonomousGuardrailsService
from app.services.governance.blast_radius_analysis import BlastRadiusAnalysisService

router = APIRouter(prefix="/admin/guardrails", tags=["commercial_autonomous_guardrails"])

guardrails_service = AutonomousGuardrailsService()
blast_radius_service = BlastRadiusAnalysisService()


class BlastRadiusPreviewPayload(BaseModel):
    action_type: str = Field(default="safe_throttle")
    target_type: str = Field(default="runtime_node")
    target_id: str | None = None
    tenant_id: str | None = None
    cluster_id: str | None = None
    affected_tenants: list[str] = Field(default_factory=list)
    target_clusters: list[str] = Field(default_factory=list)
    runtime_nodes: list[str] = Field(default_factory=list)
    destructive: bool = False
    rollback_requested: bool = False
    confidential_scope: bool = False
    federation_scope: bool = False
    sovereign_scope: bool = False


@router.get("/status")
async def get_guardrails_status(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin),
) -> dict[str, Any]:
    return await guardrails_service.summarize_status(db)


@router.get("/checkpoints")
async def list_guardrail_checkpoints(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(CommercialHumanApprovalCheckpoint).order_by(desc(CommercialHumanApprovalCheckpoint.created_at))
        )
    ).scalars().all()
    return [
        {
            "id": str(item.id),
            "tenant_id": item.tenant_id,
            "action_type": item.action_type,
            "target_type": item.target_type,
            "target_id": item.target_id,
            "checkpoint_stage": item.checkpoint_stage,
            "required_approvals": item.required_approvals,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
        }
        for item in rows
    ]


@router.get("/blast-radius")
async def get_blast_radius(
    action_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin),
) -> dict[str, Any]:
    if action_type:
        preview = blast_radius_service.score_request(
            {
                "action_type": action_type,
                "target_type": "preview",
                "affected_tenants": [],
                "target_clusters": [],
                "runtime_nodes": [],
            }
        )
        return preview
    rows = (
        await db.execute(
            select(CommercialExecutionBlastRadius).order_by(desc(CommercialExecutionBlastRadius.created_at)).limit(50)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(item.id),
                "action_type": item.action_type,
                "target_type": item.target_type,
                "target_id": item.target_id,
                "tenant_id": item.tenant_id,
                "score": item.blast_radius_score,
                "severity": item.severity,
                "blocked": item.blocked,
                "created_at": item.created_at.isoformat(),
            }
            for item in rows
        ]
    }


@router.get("/violations")
async def list_guardrail_violations(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(CommercialExecutionGuardrailEvent)
            .where(CommercialExecutionGuardrailEvent.decision == "blocked")
            .order_by(desc(CommercialExecutionGuardrailEvent.created_at))
        )
    ).scalars().all()
    return [
        {
            "id": str(item.id),
            "event_type": item.event_type,
            "severity": item.severity,
            "action_type": item.action_type,
            "summary": item.summary,
            "details_json": item.details_json or {},
            "created_at": item.created_at.isoformat(),
        }
        for item in rows
    ]


@router.get("/receipts")
async def list_guardrail_receipts(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(CommercialAutonomousExecutionReceipt).order_by(desc(CommercialAutonomousExecutionReceipt.created_at))
        )
    ).scalars().all()
    return [
        {
            "id": str(item.id),
            "tenant_id": item.tenant_id,
            "action_type": item.action_type,
            "decision": item.decision,
            "receipt_hash": item.receipt_hash,
            "previous_receipt_hash": item.previous_receipt_hash,
            "verification_status": item.verification_status,
            "created_at": item.created_at.isoformat(),
            "verified_at": item.verified_at.isoformat() if item.verified_at else None,
        }
        for item in rows
    ]
