# Owner: agent-platform
import uuid
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.api.deps import require_admin
from app.core.config import Settings, get_settings
from app.models.agents import AgentApprovalRequest, AgentRun, AgentDefinition
from app.services.auth import require_admin_role, AdminRole, admin_key_scheme, get_admin_role
from app.services.admin_rbac import is_rbac_admin_enabled, authenticate_admin_request
from app.services.agents.human_approval import (
    approve_approval_request,
    reject_approval_request,
    request_changes_for_approval_request
)

router = APIRouter(prefix="/admin/agents/approval-portal", tags=["agent-approval-portal"])

class DecideRequest(BaseModel):
    decision: str  # approved|rejected|request_changes
    reason: Optional[str] = None

def get_actor_name(admin: Any) -> str:
    if isinstance(admin, dict):
        return admin.get("email") or admin.get("username") or "admin"
    if hasattr(admin, "email") and admin.email:
        return admin.email
    if hasattr(admin, "username") and admin.username:
        return admin.username
    return "admin"

async def get_admin_actor(
    request: Request,
    x_admin_token: Optional[str] = Depends(admin_key_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> str:
    if not is_rbac_admin_enabled():
        role = get_admin_role(x_admin_token or "")
        if not role:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")
        return "admin"
    admin = await authenticate_admin_request(session=session, request=request, token=x_admin_token or "")
    return get_actor_name(admin)

@router.get("/pending")
async def list_pending_approvals(
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.READ))
):
    if not settings.agent_approval_portal_enabled:
        raise HTTPException(status_code=400, detail="Approval portal is disabled")

    # Get requests where status is pending
    stmt = (
        select(AgentApprovalRequest, AgentRun, AgentDefinition)
        .join(AgentRun, AgentApprovalRequest.agent_run_id == AgentRun.id)
        .join(AgentDefinition, AgentRun.agent_id == AgentDefinition.id)
        .where(AgentApprovalRequest.status == "pending")
    )
    res = await db.execute(stmt)
    results = res.all()

    # Format and sort by risk, expiration, tenant, agent
    items = []
    for req, run, agent in results:
        items.append({
            "id": str(req.id),
            "agent_run_id": str(req.agent_run_id),
            "risk_level": req.risk_level,
            "reason": req.reason,
            "requested_by": req.requested_by,
            "reviewer_role": req.reviewer_role,
            "status": req.status,
            "expires_at": req.expires_at.isoformat() if req.expires_at else None,
            "tenant_id": run.tenant_id,
            "agent_name": agent.name,
            "sanitized_context": req.sanitized_context,
            "created_at": req.created_at.isoformat() if req.created_at else None
        })

    # Sort risk level (critical > high > medium > low)
    risk_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    items.sort(key=lambda x: (
        risk_rank.get(x["risk_level"].lower(), 99),
        x["expires_at"] or "",
        x["tenant_id"] or "",
        x["agent_name"] or ""
    ))

    return {"items": items}

@router.get("/approvals/{id}")
async def get_approval_request(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.READ))
):
    if not settings.agent_approval_portal_enabled:
        raise HTTPException(status_code=400, detail="Approval portal is disabled")

    stmt = (
        select(AgentApprovalRequest, AgentRun)
        .join(AgentRun, AgentApprovalRequest.agent_run_id == AgentRun.id)
        .where(AgentApprovalRequest.id == id)
    )
    res = await db.execute(stmt)
    record = res.first()
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found")

    req, run = record
    return {
        "id": str(req.id),
        "agent_run_id": str(req.agent_run_id),
        "risk_level": req.risk_level,
        "reason": req.reason,
        "requested_by": req.requested_by,
        "reviewer_role": req.reviewer_role,
        "status": req.status,
        "expires_at": req.expires_at.isoformat() if req.expires_at else None,
        "sanitized_context": req.sanitized_context,
        "tenant_id": run.tenant_id,
        "created_at": req.created_at.isoformat() if req.created_at else None
    }

@router.post("/approvals/{id}/decide")
async def decide_approval_request(
    id: uuid.UUID,
    payload: DecideRequest,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    actor: str = Depends(get_admin_actor),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.WRITE))
):
    if not settings.agent_approval_portal_enabled:
        raise HTTPException(status_code=400, detail="Approval portal is disabled")

    try:
        if payload.decision == "approved":
            req = await approve_approval_request(
                db=db,
                request_id=id,
                decided_by=actor,
                caller_role=caller_role,
                reason=payload.reason
            )
        elif payload.decision == "rejected":
            req = await reject_approval_request(
                db=db,
                request_id=id,
                decided_by=actor,
                caller_role=caller_role,
                reason=payload.reason
            )
        elif payload.decision == "request_changes":
            req = await request_changes_for_approval_request(
                db=db,
                request_id=id,
                decided_by=actor,
                caller_role=caller_role,
                reason=payload.reason
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid decision value")
        
        await db.commit()
        return {"status": req.status, "id": str(req.id)}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
