# Owner: agent-platform
import uuid
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.api.deps import require_admin
from app.services.auth import require_admin_role, AdminRole, get_admin_role, admin_key_scheme
from app.services.admin_rbac import is_rbac_admin_enabled, authenticate_admin_request
from app.services.agents.human_approval import (
    approve_approval_request,
    reject_approval_request,
    request_changes_for_approval_request,
    check_and_apply_expiration,
    check_all_expired_requests,
)

router = APIRouter(prefix="/admin/agent-approvals", tags=["agent-approvals-admin"])


class DecisionRequest(BaseModel):
    decision_reason: Optional[str] = None


class ApprovalRequestResponse(BaseModel):
    id: uuid.UUID
    agent_run_id: uuid.UUID
    task_id: Optional[str] = None
    tool_invocation_id: Optional[uuid.UUID] = None
    risk_level: str
    reason: str
    requested_by: str
    reviewer_role: str
    status: str
    expires_at: str
    sanitized_context: Optional[dict] = None
    decision_reason: Optional[str] = None
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


def to_approval_response(req) -> ApprovalRequestResponse:
    return ApprovalRequestResponse(
        id=req.id,
        agent_run_id=req.agent_run_id,
        task_id=req.task_id,
        tool_invocation_id=req.tool_invocation_id,
        risk_level=req.risk_level,
        reason=req.reason,
        requested_by=req.requested_by,
        reviewer_role=req.reviewer_role,
        status=req.status,
        expires_at=req.expires_at.isoformat() if req.expires_at else "",
        sanitized_context=req.sanitized_context,
        decision_reason=req.decision_reason,
        decided_by=req.decided_by,
        decided_at=req.decided_at.isoformat() if req.decided_at else None,
        created_at=req.created_at.isoformat() if req.created_at else "",
        updated_at=req.updated_at.isoformat() if req.updated_at else "",
    )


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


@router.get("", response_model=List[ApprovalRequestResponse])
async def list_approval_requests(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
    actor: str = Depends(get_admin_actor),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.READ)),
):
    """List all approval requests, filtering by status with limit and offset."""
    await check_all_expired_requests(db)

    from app.models.agents import AgentApprovalRequest
    from sqlalchemy import select

    stmt = select(AgentApprovalRequest)
    if status:
        stmt = stmt.where(AgentApprovalRequest.status == status)
    stmt = stmt.order_by(AgentApprovalRequest.created_at.desc()).limit(limit).offset(offset)

    res = await db.execute(stmt)
    reqs = res.scalars().all()
    return [to_approval_response(r) for r in reqs]


@router.get("/{id}", response_model=ApprovalRequestResponse)
async def get_approval_request(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    actor: str = Depends(get_admin_actor),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.READ)),
):
    """Retrieve details of a specific approval request, checking for expiration on the fly."""
    from app.models.agents import AgentApprovalRequest
    from sqlalchemy import select

    stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.id == id)
    res = await db.execute(stmt)
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")

    await check_and_apply_expiration(db, req)
    return to_approval_response(req)


@router.post("/{id}/approve", response_model=ApprovalRequestResponse)
async def approve_request_endpoint(
    id: uuid.UUID,
    body: DecisionRequest,
    db: AsyncSession = Depends(get_db_session),
    actor: str = Depends(get_admin_actor),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.READ)),
):
    """Approve a pending approval request and resume the run."""
    try:
        req = await approve_approval_request(
            db=db,
            request_id=id,
            decided_by=actor,
            caller_role=caller_role,
            reason=body.decision_reason
        )
        return to_approval_response(req)
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        elif "insufficient_reviewer_role" in err_msg:
            raise HTTPException(status_code=403, detail="Insufficient permissions for this risk level")
        else:
            raise HTTPException(status_code=400, detail=err_msg)


@router.post("/{id}/reject", response_model=ApprovalRequestResponse)
async def reject_request_endpoint(
    id: uuid.UUID,
    body: DecisionRequest,
    db: AsyncSession = Depends(get_db_session),
    actor: str = Depends(get_admin_actor),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.READ)),
):
    """Reject a pending approval request and terminate the run."""
    try:
        req = await reject_approval_request(
            db=db,
            request_id=id,
            decided_by=actor,
            caller_role=caller_role,
            reason=body.decision_reason
        )
        return to_approval_response(req)
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        elif "insufficient_reviewer_role" in err_msg:
            raise HTTPException(status_code=403, detail="Insufficient permissions for this risk level")
        else:
            raise HTTPException(status_code=400, detail=err_msg)


@router.post("/{id}/request-changes", response_model=ApprovalRequestResponse)
async def request_changes_endpoint(
    id: uuid.UUID,
    body: DecisionRequest,
    db: AsyncSession = Depends(get_db_session),
    actor: str = Depends(get_admin_actor),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.READ)),
):
    """Request changes for a pending approval request, pausing the run."""
    try:
        req = await request_changes_for_approval_request(
            db=db,
            request_id=id,
            decided_by=actor,
            caller_role=caller_role,
            reason=body.decision_reason
        )
        return to_approval_response(req)
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        elif "insufficient_reviewer_role" in err_msg:
            raise HTTPException(status_code=403, detail="Insufficient permissions for this risk level")
        else:
            raise HTTPException(status_code=400, detail=err_msg)

@router.get("/inbox")
async def get_approvals_inbox(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin)
) -> List[Dict[str, Any]]:
    # Order by risk and expiration
    return []
