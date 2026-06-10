# Owner: agent-platform
import uuid
from typing import Optional

from app.api import deps
from app.services.agents.debugger.breakpoints import BreakpointManager
from app.services.agents.debugger.debug_sessions import DebugSessionManager
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/admin/debugger", tags=["agent-debugger"])

@router.post("/sessions/{run_id}/pause")
async def pause_session(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user) # RBAC: Admin/Dev required
):
    manager = DebugSessionManager(db)
    session = await manager.get_or_create_session(run_id, current_user.tenant_id)
    await manager.pause_session(session.id)
    return {"status": "paused", "session_id": str(session.id)}

@router.post("/sessions/{run_id}/resume")
async def resume_session(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    manager = DebugSessionManager(db)
    session = await manager.get_or_create_session(run_id, current_user.tenant_id)
    await manager.resume_session(session.id)
    return {"status": "active", "session_id": str(session.id)}

@router.post("/breakpoints/{run_id}")
async def add_breakpoint(
    run_id: uuid.UUID,
    type: str,
    target: Optional[str] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    manager = BreakpointManager(db)
    bp = await manager.add_breakpoint(run_id, type, target)
    return {"status": "created", "breakpoint_id": str(bp.id)}

@router.get("/sessions/{run_id}/state")
async def get_session_state(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    from app.models.agents.agent_debugger import AgentDebugStepEvent
    from sqlalchemy import select
    
    manager = DebugSessionManager(db)
    session = await manager.get_or_create_session(run_id, current_user.tenant_id)
    
    stmt = select(AgentDebugStepEvent).where(
        AgentDebugStepEvent.session_id == session.id
    ).order_by(AgentDebugStepEvent.step_number.desc()).limit(1)
    
    res = await db.execute(stmt)
    latest_event = res.scalar_one_or_none()
    
    return {
        "session_status": session.status,
        "current_step": session.current_step,
        "latest_event": latest_event
    }
