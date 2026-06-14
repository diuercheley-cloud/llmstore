# Owner: agent-platform
import uuid
from typing import Any, Dict, List, Optional

from app.api.deps import require_admin
from app.services.runtime_dependencies import get_db_session
from app.models.agents.agent_routing import (
    AgentModelCapability,
    AgentRoutingPolicy,
    AgentStepRoutingDecision,
)
from app.services.agents.routing.agentic_router import AgenticRouterV2
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/routing", tags=["agent-routing-admin"])

# Schemas
class ModelCapabilitySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    model_id: str
    provider: str
    supports_tool_calling: bool
    supports_json_mode: bool
    context_window: int
    cost_input: float
    cost_output: float
    latency_class: str
    quality_tier: int
    recommended_step_classes: Optional[List[str]] = None

class RoutingPolicySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    rules: Dict[str, Any]
    priority: int = 0
    is_active: bool = True

class SimulationRequest(BaseModel):
    step_type: str
    input_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    policy_name: str = "balanced"
    profile_name: Optional[str] = None

class SimulationResponse(BaseModel):
    chosen_model_id: str
    step_class: str
    explanation: str

class RoutingDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    run_id: uuid.UUID
    step_id: Optional[uuid.UUID]
    step_class: str
    chosen_model_id: str
    policy_applied: Optional[str]
    explanation: Optional[str]
    created_at: Any

@router.get("/capabilities", response_model=List[ModelCapabilitySchema])
async def get_capabilities(
    db: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin)
):
    result = await db.execute(select(AgentModelCapability))
    return list(result.scalars().all())

@router.post("/policies", response_model=RoutingPolicySchema)
async def create_policy(
    policy: RoutingPolicySchema,
    db: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin)
):
    db_policy = AgentRoutingPolicy(**policy.model_dump())
    db.add(db_policy)
    await db.commit()
    await db.refresh(db_policy)
    return db_policy

@router.post("/simulate", response_model=SimulationResponse)
async def simulate_routing(
    request: SimulationRequest,
    db: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin)
):
    router_v2 = AgenticRouterV2(db)
    # Mocking a run_id for simulation
    mock_run_id = uuid.uuid4()
    
    try:
        model_id = await router_v2.route_step(
            run_id=mock_run_id,
            step_type=request.step_type,
            input_text=request.input_text,
            metadata=request.metadata,
            policy_name=request.policy_name,
            profile_name=request.profile_name
        )
        
        result = await db.execute(select(AgentStepRoutingDecision).filter(AgentStepRoutingDecision.run_id == mock_run_id))
        decision = result.scalars().first()
        
        return SimulationResponse(
            chosen_model_id=model_id,
            step_class=decision.step_class,
            explanation=decision.explanation
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/decisions", response_model=List[RoutingDecisionResponse])
async def get_decisions(
    run_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin)
):
    stmt = select(AgentStepRoutingDecision)
    if run_id:
        stmt = stmt.filter(AgentStepRoutingDecision.run_id == run_id)
    
    result = await db.execute(stmt.order_by(AgentStepRoutingDecision.created_at.desc()).limit(100))
    return list(result.scalars().all())
