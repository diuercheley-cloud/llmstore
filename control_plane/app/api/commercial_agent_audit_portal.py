# Owner: agent-platform
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.commercial.commercial_agents import (
    CommercialAgentAction,
    CommercialAgentExecution,
    CommercialAgentReplayRecord,
)
from app.models.core.client import Client
from app.services.auth import require_client
from app.services.runtime_dependencies import get_db_session
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/portal/agents/audit", tags=["portal", "trusted-agent-audit"])


@router.get("/executions")
async def list_portal_agent_executions(
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    tenant_id = str(client.id)
    rows = (
        (
            await db.execute(
                select(CommercialAgentExecution)
                .where(CommercialAgentExecution.tenant_id == tenant_id)
                .order_by(desc(CommercialAgentExecution.started_at))
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
                "plan_hash": row.plan_hash,
                "execution_graph_hash": row.execution_graph_hash,
                "replay_status": row.replay_status,
                "approval_status": row.approval_status,
                "started_at": row.started_at.isoformat() if row.started_at else None,
            }
            for row in rows
        ]
    }


@router.get("/actions")
async def list_portal_agent_actions(
    execution_id: UUID | None = None,
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    tenant_id = str(client.id)
    stmt = (
        select(CommercialAgentAction)
        .where(CommercialAgentAction.tenant_id == tenant_id)
        .order_by(desc(CommercialAgentAction.executed_at))
        .limit(200)
    )
    if execution_id:
        stmt = stmt.where(CommercialAgentAction.execution_id == execution_id)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "items": [
            {
                "id": str(row.id),
                "execution_id": str(row.execution_id),
                "tool_name": row.tool_name,
                "status": row.status,
                "receipt_hash": row.receipt_hash,
                "approval_status": row.approval_status,
                "policy_reason": (row.policy_decision_json or {}).get("reason"),
                "executed_at": row.executed_at.isoformat() if row.executed_at else None,
            }
            for row in rows
        ]
    }


@router.get("/replay")
async def list_portal_agent_replays(
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    tenant_id = str(client.id)
    rows = (
        (
            await db.execute(
                select(CommercialAgentReplayRecord)
                .where(CommercialAgentReplayRecord.tenant_id == tenant_id)
                .order_by(desc(CommercialAgentReplayRecord.created_at))
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
                "execution_id": str(row.execution_id),
                "verification_result": row.verification_result,
                "mismatch_reason": row.mismatch_reason,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }


@router.get("/violations")
async def list_portal_agent_violations(
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(100, ge=1, le=200),
) -> dict[str, Any]:
    tenant_id = str(client.id)
    rows = (
        (
            await db.execute(
                select(CommercialAgentAction)
                .where(
                    CommercialAgentAction.tenant_id == tenant_id,
                    CommercialAgentAction.status == "denied",
                )
                .order_by(desc(CommercialAgentAction.executed_at))
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "id": str(row.id),
                "tool_name": row.tool_name,
                "reason": (row.policy_decision_json or {}).get("reason"),
                "executed_at": row.executed_at.isoformat() if row.executed_at else None,
            }
            for row in rows
        ]
    }


@router.get("/executions/{execution_id}")
async def get_portal_agent_execution(
    execution_id: UUID,
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    execution = await db.get(CommercialAgentExecution, execution_id)
    if execution is None or execution.tenant_id != str(client.id):
        raise HTTPException(status_code=404, detail="execution_not_found")
    return {
        "id": str(execution.id),
        "status": execution.status,
        "plan_hash": execution.plan_hash,
        "execution_graph_hash": execution.execution_graph_hash,
        "runtime_snapshot_hash": execution.runtime_snapshot_hash,
        "audit_chain_hash": execution.audit_chain_hash,
        "replay_status": execution.replay_status,
    }
