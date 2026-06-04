# Owner: Platform Operations
import uuid
from typing import Any, Dict, List, Optional

from app.db.session import get_db_session
from app.models.multi_agent import AgentTeamTrace
from app.services.agents.multi_agent.debate_runtime import DebateRuntime
from app.services.agents.multi_agent.dynamic_runtime import DynamicRoutingRuntime
from app.services.agents.multi_agent.hierarchical_runtime import HierarchicalRuntime
from app.services.agents.multi_agent.team_registry import TeamRegistry
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/teams", tags=["agent-multi-agent-admin"])

# Schemas
class TeamMemberCreate(BaseModel):
    agent_id: uuid.UUID
    role: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TeamCreate(BaseModel):
    name: str
    topology: str # hierarchical|debate|dynamic
    owner_user_id: str
    description: Optional[str] = None
    members: List[TeamMemberCreate] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)

class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    topology: str
    status: str

class TeamRunRequest(BaseModel):
    goal: str
    work_items: List[Dict[str, Any]] = Field(default_factory=list)

# Endpoints
@router.post("", response_model=TeamResponse)
async def create_team(payload: TeamCreate, db: AsyncSession = Depends(get_db_session)):
    registry = TeamRegistry(db)
    team = await registry.create_team(
        tenant_id="default",
        name=payload.name,
        topology=payload.topology,
        owner_user_id=payload.owner_user_id,
        description=payload.description,
        config=payload.config
    )
    
    for m in payload.members:
        await registry.add_member(team.id, m.agent_id, m.role, m.metadata)
        
    await db.commit()
    return team

@router.get("", response_model=List[TeamResponse])
async def list_teams(tenant_id: str = "default", db: AsyncSession = Depends(get_db_session)):
    registry = TeamRegistry(db)
    return await registry.list_teams(tenant_id)

@router.post("/{id}/runs")
async def run_team(id: uuid.UUID, payload: TeamRunRequest, db: AsyncSession = Depends(get_db_session)):
    registry = TeamRegistry(db)
    team = await registry.get_team(id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
        
    if team.topology == "hierarchical":
        runtime = HierarchicalRuntime(db)
        result = await runtime.execute(team.id, payload.goal)
    elif team.topology == "debate":
        runtime = DebateRuntime(db)
        result = await runtime.execute(team.id, payload.goal)
    elif team.topology == "dynamic":
        runtime = DynamicRoutingRuntime(db)
        result = await runtime.execute(team.id, payload.goal, work_items=payload.work_items)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported topology: {team.topology}")
        
    return {"status": "completed", "result": result}

@router.get("/runs/{run_id}/trace")
async def get_team_run_trace(run_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    from sqlalchemy import select
    stmt = select(AgentTeamTrace).where(AgentTeamTrace.run_id == run_id).order_by(AgentTeamTrace.created_at.asc())
    res = await db.execute(stmt)
    return res.scalars().all()
