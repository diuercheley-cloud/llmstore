# Owner: agent-platform
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.session import get_db_session
from app.models.client import Client
from app.models.commercial_workflows import (
    CommercialWorkflowExecution,
    CommercialWorkflowPolicySnapshot,
    CommercialWorkflowReceipt,
    CommercialWorkflowReplaySession,
)
from app.services.auth import require_client
from app.services.workflows.workflow_governance_ledger import WorkflowGovernanceLedgerService
from app.services.workflows.workflow_provenance import WorkflowProvenanceService
from app.services.workflows.workflow_receipts import WorkflowReceiptService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/portal/workflows/audit", tags=["portal", "workflows-audit"])

_provenance = WorkflowProvenanceService()
_receipts = WorkflowReceiptService()
_ledger = WorkflowGovernanceLedgerService()


@router.get("/executions")
async def list_workflow_executions(
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    tenant_id = str(client.id)
    rows = (
        await db.execute(
            select(CommercialWorkflowExecution)
            .where(CommercialWorkflowExecution.tenant_id == tenant_id)
            .order_by(desc(CommercialWorkflowExecution.started_at))
            .limit(100)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(row.id),
                "status": row.status,
                "determinism_status": row.determinism_status,
                "ledger_hash": row.ledger_hash,
                "dag_hash": row.dag_hash,
                "started_at": row.started_at.isoformat() if row.started_at else None,
            }
            for row in rows
        ]
    }


@router.get("/receipts")
async def list_workflow_receipts(
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    tenant_id = str(client.id)
    rows = (
        await db.execute(
            select(CommercialWorkflowReceipt)
            .where(CommercialWorkflowReceipt.tenant_id == tenant_id)
            .order_by(desc(CommercialWorkflowReceipt.created_at))
            .limit(100)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(row.id),
                "execution_id": str(row.execution_id),
                "receipt_hash": row.receipt_hash,
                "verification_status": row.verification_status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }


@router.get("/provenance/{execution_id}")
async def get_workflow_provenance(
    execution_id: UUID,
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    execution = await db.get(CommercialWorkflowExecution, execution_id)
    if execution is None or execution.tenant_id != str(client.id):
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    return await _provenance.build_execution_provenance(db, execution)


@router.get("/determinism/{execution_id}")
async def get_workflow_determinism(
    execution_id: UUID,
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    execution = await db.get(CommercialWorkflowExecution, execution_id)
    if execution is None or execution.tenant_id != str(client.id):
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    receipts = (
        await db.execute(
            select(CommercialWorkflowReceipt)
            .where(CommercialWorkflowReceipt.execution_id == execution_id)
            .order_by(desc(CommercialWorkflowReceipt.created_at))
            .limit(1)
        )
    ).scalars().all()
    receipt = receipts[0] if receipts else None
    verification = await _receipts.verify_receipt(db, receipt) if receipt else None
    await db.commit()
    return {
        "execution_id": str(execution.id),
        "status": execution.status,
        "determinism_status": execution.determinism_status,
        "ledger_hash": execution.ledger_hash,
        "receipt_verification": verification,
    }


@router.get("/governance/executions")
async def list_governed_executions(
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(CommercialWorkflowExecution)
            .where(CommercialWorkflowExecution.tenant_id == str(client.id))
            .order_by(desc(CommercialWorkflowExecution.started_at))
            .limit(100)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(row.id),
                "status": row.status,
                "governance_status": row.governance_status,
                "governance_ledger_hash": row.governance_ledger_hash,
                "replay_status": row.replay_status,
            }
            for row in rows
        ]
    }


@router.get("/governance/{execution_id}")
async def get_governance_view(
    execution_id: UUID,
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    execution = await db.get(CommercialWorkflowExecution, execution_id)
    if execution is None or execution.tenant_id != str(client.id):
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    snapshots = (
        await db.execute(
            select(CommercialWorkflowPolicySnapshot)
            .where(CommercialWorkflowPolicySnapshot.execution_id == execution.id)
            .order_by(CommercialWorkflowPolicySnapshot.created_at.asc())
        )
    ).scalars().all()
    events = await _ledger.list_events(db, execution_id=execution.id)
    return {
        "execution_id": str(execution.id),
        "governance_status": execution.governance_status,
        "ledger_hash": execution.governance_ledger_hash,
        "policy_snapshots": [
            {
                "id": str(row.id),
                "snapshot_hash": row.snapshot_hash,
                "policy_hash": row.policy_hash,
                "runtime_context_hash": row.runtime_context_hash,
            }
            for row in snapshots
        ],
        "events": [
            {
                "id": str(row.id),
                "event_type": row.event_type,
                "event_summary": row.event_summary,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in events
        ],
    }


@router.get("/replay/sessions")
async def list_replay_sessions(
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(CommercialWorkflowReplaySession)
            .where(CommercialWorkflowReplaySession.tenant_id == str(client.id))
            .order_by(desc(CommercialWorkflowReplaySession.created_at))
            .limit(100)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(row.id),
                "original_execution_id": str(row.original_execution_id),
                "replay_execution_id": str(row.replay_execution_id) if row.replay_execution_id else None,
                "session_status": row.session_status,
                "policy_mismatch_detected": row.policy_mismatch_detected,
                "report_hash": row.report_hash,
            }
            for row in rows
        ]
    }
