# Owner: agent-platform
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.commercial.commercial_workflows import (
    CommercialWorkflowExecution,
    CommercialWorkflowPolicySnapshot,
    CommercialWorkflowReplaySession,
)
from app.models.core.client import Client
from app.services.auth import require_client
from app.services.runtime_dependencies import get_db_session
from app.services.workflows.workflow_governance_ledger import WorkflowGovernanceLedgerService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["portal", "workflows-governance"])

_ledger = WorkflowGovernanceLedgerService()


@router.get("/portal/workflows/governance/executions")
async def list_governance_executions(
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    rows = (
        (
            await db.execute(
                select(CommercialWorkflowExecution)
                .where(CommercialWorkflowExecution.tenant_id == str(client.id))
                .order_by(desc(CommercialWorkflowExecution.started_at))
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
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


@router.get("/portal/workflows/governance/executions/{execution_id}")
async def get_governance_execution(
    execution_id: UUID,
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    execution = await db.get(CommercialWorkflowExecution, execution_id)
    if execution is None or execution.tenant_id != str(client.id):
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    snapshots = (
        (
            await db.execute(
                select(CommercialWorkflowPolicySnapshot)
                .where(CommercialWorkflowPolicySnapshot.execution_id == execution.id)
                .order_by(CommercialWorkflowPolicySnapshot.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    events = await _ledger.list_events(db, execution_id=execution.id)
    return {
        "execution_id": str(execution.id),
        "governance_status": execution.governance_status,
        "ledger_hash": execution.governance_ledger_hash,
        "snapshots": [
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


@router.get("/portal/workflows/replay/sessions")
async def list_replay_sessions(
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    rows = (
        (
            await db.execute(
                select(CommercialWorkflowReplaySession)
                .where(CommercialWorkflowReplaySession.tenant_id == str(client.id))
                .order_by(desc(CommercialWorkflowReplaySession.created_at))
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "id": str(row.id),
                "original_execution_id": str(row.original_execution_id),
                "replay_execution_id": str(row.replay_execution_id)
                if row.replay_execution_id
                else None,
                "session_status": row.session_status,
                "policy_mismatch_detected": row.policy_mismatch_detected,
                "mismatch_detected": row.mismatch_detected,
                "report_hash": row.report_hash,
            }
            for row in rows
        ]
    }
