# Owner: agent-platform
import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..api.dependencies import get_admin_user
from ..db.session import get_db
from ..models.commercial.commercial_agents import (
    CommercialAgentExecution,
    CommercialAgentProfile,
    CommercialAgentToolExecution,
)
from ..services.inference import agent_governance

router = APIRouter(prefix="/admin/inference/agents", tags=["Agent Governance Admin"])

@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    return await agent_governance.summarize_agent_governance(db)

@router.get("/profiles", response_model=List[dict])
async def list_profiles(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialAgentProfile).order_by(CommercialAgentProfile.created_at.desc()))
    profiles = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "agent_name": p.agent_name,
            "client_id": p.client_id,
            "enabled": p.enabled,
            "can_delegate": p.can_delegate,
            "allowed_tools": p.allowed_tools,
            "created_at": p.created_at.isoformat()
        }
        for p in profiles
    ]

@router.post("/profiles")
async def create_profile(payload: dict, db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    profile = await agent_governance.create_agent_profile(
        db, 
        agent_name=payload["agent_name"],
        client_id=payload.get("client_id"),
        allowed_tools=payload.get("allowed_tools", []),
        can_delegate=payload.get("can_delegate", False)
    )
    return profile

@router.get("/executions", response_model=List[dict])
async def list_executions(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialAgentExecution).order_by(CommercialAgentExecution.started_at.desc()).limit(100))
    executions = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "agent_id": str(e.agent_id),
            "session_id": e.session_id,
            "status": e.status,
            "started_at": e.started_at.isoformat()
        }
        for e in executions
    ]

@router.get("/tool-executions", response_model=List[dict])
async def list_tool_executions(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialAgentToolExecution).order_by(CommercialAgentToolExecution.executed_at.desc()).limit(100))
    tools = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "execution_id": str(t.execution_id),
            "tool_name": t.tool_name,
            "approval_status": t.approval_status,
            "executed_at": t.executed_at.isoformat()
        }
        for t in tools
    ]

@router.post("/tool-executions/{id}/approve")
async def approve_tool(id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialAgentToolExecution).where(CommercialAgentToolExecution.id == id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool execution not found")
        
    tool.approval_status = "approved"
    await db.commit()
    return {"status": "approved"}
