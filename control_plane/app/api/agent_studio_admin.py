# Owner: Platform Operations
import uuid
from typing import Any, Dict, List, Optional

from app.db.session import get_db_session
from app.models.agent_studio import (
    AgentFlowDebugSession,
    AgentFlowDefinition,
    AgentFlowVersion,
)
from app.services.agents.studio.flow_compiler import FlowCompiler
from app.services.agents.studio.flow_validator import FlowValidator
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/studio", tags=["agent-studio-admin"])

# Schemas
class FlowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    graph_json: Dict[str, Any] = Field(default_factory=dict)

class FlowResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: Any

# Endpoints
@router.post("/flows", response_model=FlowResponse)
async def create_flow(payload: FlowCreate, db: AsyncSession = Depends(get_db_session)):
    flow = AgentFlowDefinition(
        tenant_id="default",
        name=payload.name,
        description=payload.description
    )
    db.add(flow)
    await db.flush()
    
    version = AgentFlowVersion(
        flow_id=flow.id,
        version_label="v1",
        is_active=True,
        graph_json=payload.graph_json
    )
    db.add(version)
    
    await db.commit()
    return flow

@router.get("/flows", response_model=List[FlowResponse])
async def list_flows(db: AsyncSession = Depends(get_db_session)):
    stmt = select(AgentFlowDefinition).where(AgentFlowDefinition.tenant_id == "default")
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/flows/{id}")
async def get_flow(id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    stmt = select(AgentFlowDefinition).where(AgentFlowDefinition.id == id)
    res = await db.execute(stmt)
    flow = res.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    # Get active version
    stmt_v = select(AgentFlowVersion).where(AgentFlowVersion.flow_id == id, AgentFlowVersion.is_active == True)
    res_v = await db.execute(stmt_v)
    version = res_v.scalar_one_or_none()
    
    return {
        "id": flow.id,
        "name": flow.name,
        "description": flow.description,
        "active_version": version
    }

@router.post("/flows/{id}/validate")
async def validate_flow(id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    stmt = select(AgentFlowVersion).where(AgentFlowVersion.flow_id == id, AgentFlowVersion.is_active == True)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Active flow version not found")
        
    validator = FlowValidator()
    errors = validator.validate(version)
    
    return {"status": "valid" if not errors else "invalid", "errors": errors}

@router.post("/flows/{id}/compile")
async def compile_flow(id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    stmt = select(AgentFlowVersion).where(AgentFlowVersion.flow_id == id, AgentFlowVersion.is_active == True)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Active flow version not found")
        
    compiler = FlowCompiler()
    plan_data = compiler.compile(version)
    
    return {"status": "compiled", "plan": plan_data}

@router.get("/debug/{run_id}")
async def get_debug_session(run_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    stmt = select(AgentFlowDebugSession).where(AgentFlowDebugSession.run_id == run_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
         raise HTTPException(status_code=404, detail="Debug session not found")
         
    stmt_e = select(AgentDebugEvent).where(AgentDebugEvent.session_id == session.id).order_by(AgentDebugEvent.created_at.asc())
    res_e = await db.execute(stmt_e)
    events = res_e.scalars().all()
    
    return {"session": session, "events": events}
