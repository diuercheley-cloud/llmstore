# Owner: agent-platform
from __future__ import annotations

import uuid
from typing import Any

from app.db.session import get_db_session
from app.models.commercial.commercial_agents import (
    CommercialAgentAction,
    CommercialAgentExecution,
    CommercialAgentProfile,
    CommercialAgentReplayRecord,
    CommercialToolApproval,
    CommercialToolRegistry,
)
from app.services.agents.action_replay import verify_execution_replay
from app.services.agents.execution_receipts import canonical_json, sha256_hex
from app.services.agents.tool_policy_engine import ToolPolicyEngine
from app.services.agents.trusted_agent_runtime import trusted_agent_runtime
from app.services.auth import require_admin
from app.utils.crypto_signer import sign_payload
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    tags=["admin", "trusted-agent-runtime"],
    dependencies=[Depends(require_admin)],
)

policy_engine = ToolPolicyEngine()


class ToolRegistryPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tool_name: str = Field(min_length=1, max_length=128)
    tenant_id: str | None = None
    enabled: bool = True
    trust_status: str = "trusted"
    execution_mode: str = "internal"
    requires_approval: bool = False
    allow_dry_run: bool = True
    confidential_payload_mode: str = "redacted"
    rate_limit_per_minute: int = 120
    quota_limit_per_day: int = 5000
    signer_identity: str | None = None
    policy_scope_json: dict[str, Any] | None = None
    schema_definition: dict[str, Any] | None = Field(default=None, alias="schema_json")
    metadata_json: dict[str, Any] | None = None


class ExecutionPlanPayload(BaseModel):
    agent_id: uuid.UUID
    tenant_id: str
    session_id: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    action_plan: list[dict[str, Any]]
    runtime_mode: str = "enforce"
    dry_run: bool = False


class ApprovalDecisionPayload(BaseModel):
    approved_by: str = Field(min_length=1, max_length=255)
    status: str = Field(pattern="^(approved|rejected)$")
    decision_reason: str | None = None


@router.get("/admin/agents/runtime/status")
async def get_runtime_status(db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    return await trusted_agent_runtime.summarize_runtime(db)


@router.post("/admin/agents/runtime/plans")
async def create_runtime_plan(payload: ExecutionPlanPayload, db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    execution = await trusted_agent_runtime.create_execution(
        db,
        agent_id=payload.agent_id,
        tenant_id=payload.tenant_id,
        session_id=payload.session_id,
        input_payload=payload.input_payload,
        action_plan=payload.action_plan,
        runtime_mode=payload.runtime_mode,
        dry_run=payload.dry_run,
    )
    await db.commit()
    await db.refresh(execution)
    return {
        "execution_id": str(execution.id),
        "plan_hash": execution.plan_hash,
        "execution_graph_hash": execution.execution_graph_hash,
        "runtime_snapshot_hash": execution.runtime_snapshot_hash,
        "status": execution.status,
    }


@router.post("/admin/agents/runtime/execute/{execution_id}")
async def execute_runtime_plan(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    execution = await trusted_agent_runtime.execute_plan(db, execution_id=execution_id)
    await db.commit()
    await db.refresh(execution)
    return {
        "execution_id": str(execution.id),
        "status": execution.status,
        "policy_decision": execution.policy_decision,
        "approval_status": execution.approval_status,
        "audit_chain_hash": execution.audit_chain_hash,
    }


@router.get("/admin/agents/runtime/executions")
async def list_runtime_executions(
    tenant_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    stmt = select(CommercialAgentExecution).order_by(desc(CommercialAgentExecution.started_at)).limit(100)
    if tenant_id:
        stmt = stmt.where(CommercialAgentExecution.tenant_id == tenant_id)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(row.id),
            "agent_id": str(row.agent_id),
            "tenant_id": row.tenant_id,
            "status": row.status,
            "plan_hash": row.plan_hash,
            "execution_graph_hash": row.execution_graph_hash,
            "replay_status": row.replay_status,
            "approval_status": row.approval_status,
            "started_at": row.started_at.isoformat() if row.started_at else None,
        }
        for row in rows
    ]


@router.get("/admin/agents/tools")
async def list_trusted_tools(
    tenant_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    stmt = select(CommercialToolRegistry).order_by(desc(CommercialToolRegistry.updated_at))
    if tenant_id:
        stmt = stmt.where(CommercialToolRegistry.tenant_id == tenant_id)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(row.id),
            "tool_name": row.tool_name,
            "tenant_id": row.tenant_id,
            "enabled": row.enabled,
            "trust_status": row.trust_status,
            "requires_approval": row.requires_approval,
            "confidential_payload_mode": row.confidential_payload_mode,
            "rate_limit_per_minute": row.rate_limit_per_minute,
            "quota_limit_per_day": row.quota_limit_per_day,
        }
        for row in rows
    ]


@router.post("/admin/agents/tools")
async def register_trusted_tool(payload: ToolRegistryPayload, db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    payload_data = payload.model_dump(by_alias=True)
    row = CommercialToolRegistry(
        **payload_data,
        provenance_hash=sha256_hex(canonical_json(payload_data)),
        provenance_signature=sign_payload(f"{sha256_hex(payload.tool_name)[:24]}"),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "id": str(row.id),
        "tool_name": row.tool_name,
        "provenance_hash": row.provenance_hash,
        "trust_status": row.trust_status,
    }


@router.get("/admin/agents/tools/approvals")
async def list_tool_approvals(
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    stmt = select(CommercialToolApproval).order_by(desc(CommercialToolApproval.created_at)).limit(100)
    if status:
        stmt = stmt.where(CommercialToolApproval.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(row.id),
            "action_id": str(row.action_id),
            "execution_id": str(row.execution_id),
            "tenant_id": row.tenant_id,
            "status": row.status,
            "approved_by": row.approved_by,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.post("/admin/agents/tools/approvals/{action_id}")
async def decide_tool_approval(
    action_id: uuid.UUID,
    payload: ApprovalDecisionPayload,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    approval = await trusted_agent_runtime.approve_action(
        db,
        action_id=action_id,
        approved_by=payload.approved_by,
        status=payload.status,
        decision_reason=payload.decision_reason,
    )
    await db.commit()
    return {
        "id": str(approval.id),
        "status": approval.status,
        "approved_by": approval.approved_by,
    }


@router.post("/admin/agents/replay/verify/{execution_id}")
async def verify_replay(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    replay = await verify_execution_replay(db, execution_id=execution_id, verified_by="admin")
    await db.commit()
    return {
        "id": str(replay.id),
        "verification_result": replay.verification_result,
        "mismatch_reason": replay.mismatch_reason,
    }


@router.get("/admin/agents/replay/records")
async def list_replay_records(db: AsyncSession = Depends(get_db_session)) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(CommercialAgentReplayRecord).order_by(desc(CommercialAgentReplayRecord.created_at)).limit(100)
        )
    ).scalars().all()
    return [
        {
            "id": str(row.id),
            "execution_id": str(row.execution_id),
            "tenant_id": row.tenant_id,
            "verification_result": row.verification_result,
            "mismatch_reason": row.mismatch_reason,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/admin/agents/replay/violations")
async def list_policy_violations(
    tenant_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    return await policy_engine.summarize_policy_violations(db, tenant_id=tenant_id)


@router.get("/admin/agents/runtime/actions/{execution_id}")
async def list_execution_actions(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)) -> list[dict[str, Any]]:
    execution = await db.get(CommercialAgentExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="execution_not_found")
    rows = (
        await db.execute(
            select(CommercialAgentAction)
            .where(CommercialAgentAction.execution_id == execution_id)
            .order_by(CommercialAgentAction.action_index.asc())
        )
    ).scalars().all()
    return [
        {
            "id": str(row.id),
            "tool_name": row.tool_name,
            "status": row.status,
            "receipt_hash": row.receipt_hash,
            "approval_status": row.approval_status,
        }
        for row in rows
    ]


@router.get("/admin/agents/runtime/profiles")
async def list_runtime_profiles(db: AsyncSession = Depends(get_db_session)) -> list[dict[str, Any]]:
    rows = (await db.execute(select(CommercialAgentProfile).order_by(desc(CommercialAgentProfile.created_at)).limit(100))).scalars().all()
    return [
        {
            "id": str(row.id),
            "agent_name": row.agent_name,
            "client_id": row.client_id,
            "allowed_tenants_json": row.allowed_tenants_json,
            "max_actions_per_minute": row.max_actions_per_minute,
            "max_actions_per_day": row.max_actions_per_day,
        }
        for row in rows
    ]
