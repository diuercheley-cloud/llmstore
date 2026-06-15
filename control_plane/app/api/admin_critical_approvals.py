import uuid
from typing import Any

from app.services.admin_rbac import authenticate_admin_request, is_rbac_admin_enabled
from app.services.approval_service import ApprovalService, approvals_ws_manager
from app.services.auth import AdminRole, admin_key_scheme, get_admin_role, require_admin_role
from app.services.runtime_dependencies import get_db_session
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/approvals", tags=["critical-approvals-admin"])


class CriticalApprovalCreate(BaseModel):
    action_type: str
    description: str
    payload: dict | None = None
    metadata_json: dict | None = None
    expires_in_seconds: int = 3600


class DecisionRequest(BaseModel):
    decision_reason: str | None = None


class CriticalApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action_type: str
    description: str
    status: str
    requested_by: str
    requested_at: str
    decided_by: str | None = None
    decided_at: str | None = None
    decision_reason: str | None = None
    expires_at: str
    payload: dict | None = None
    metadata_json: dict | None = None


def to_approval_response(req) -> CriticalApprovalResponse:
    return CriticalApprovalResponse(
        id=req.id,
        action_type=req.action_type,
        description=req.description,
        status=req.status,
        requested_by=req.requested_by,
        requested_at=req.requested_at.isoformat() if req.requested_at else "",
        decided_by=req.decided_by,
        decided_at=req.decided_at.isoformat() if req.decided_at else None,
        decision_reason=req.decision_reason,
        expires_at=req.expires_at.isoformat() if req.expires_at else "",
        payload=req.payload,
        metadata_json=req.metadata_json,
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
    x_admin_token: str | None = Depends(admin_key_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> str:
    if not is_rbac_admin_enabled():
        role = get_admin_role(x_admin_token or "")
        if not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token"
            )
        return "admin"
    admin = await authenticate_admin_request(
        session=session, request=request, token=x_admin_token or ""
    )
    return get_actor_name(admin)


@router.post("", response_model=CriticalApprovalResponse)
async def create_critical_approval(
    body: CriticalApprovalCreate,
    db: AsyncSession = Depends(get_db_session),
    actor: str = Depends(get_admin_actor),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.WRITE)),
):
    """Create a critical approval request."""
    req = await ApprovalService.create_request(
        db=db,
        action_type=body.action_type,
        description=body.description,
        requested_by=actor,
        payload=body.payload,
        metadata=body.metadata_json,
        expires_in_seconds=body.expires_in_seconds,
    )
    return to_approval_response(req)


@router.get("", response_model=list[CriticalApprovalResponse])
async def list_critical_approvals(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
    actor: str = Depends(get_admin_actor),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.READ)),
):
    """List all critical approval requests."""
    reqs = await ApprovalService.list_requests(
        db=db,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [to_approval_response(r) for r in reqs]


@router.get("/{id}", response_model=CriticalApprovalResponse)
async def get_critical_approval(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    actor: str = Depends(get_admin_actor),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.READ)),
):
    """Retrieve details of a specific critical approval request."""
    try:
        req = await ApprovalService.get_request(db=db, request_id=id)
        return to_approval_response(req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{id}/approve", response_model=CriticalApprovalResponse)
async def approve_critical_approval(
    id: uuid.UUID,
    body: DecisionRequest,
    db: AsyncSession = Depends(get_db_session),
    actor: str = Depends(get_admin_actor),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.WRITE)),
):
    """Approve a pending critical approval request."""
    try:
        req = await ApprovalService.approve_request(
            db=db,
            request_id=id,
            decided_by=actor,
            reason=body.decision_reason,
        )
        return to_approval_response(req)
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        else:
            raise HTTPException(status_code=400, detail=err_msg)


@router.post("/{id}/reject", response_model=CriticalApprovalResponse)
async def reject_critical_approval(
    id: uuid.UUID,
    body: DecisionRequest,
    db: AsyncSession = Depends(get_db_session),
    actor: str = Depends(get_admin_actor),
    caller_role: AdminRole = Depends(require_admin_role(AdminRole.WRITE)),
):
    """Reject a pending critical approval request."""
    try:
        req = await ApprovalService.reject_request(
            db=db,
            request_id=id,
            decided_by=actor,
            reason=body.decision_reason,
        )
        return to_approval_response(req)
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        else:
            raise HTTPException(status_code=400, detail=err_msg)


@router.websocket("/ws")
async def approvals_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for receiving real-time approval events."""
    await approvals_ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for any messages if client sends them
            await websocket.receive_text()
    except WebSocketDisconnect:
        approvals_ws_manager.disconnect(websocket)
