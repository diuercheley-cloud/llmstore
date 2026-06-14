# Owner: Platform Operations
import uuid
from typing import Any, Dict, List, Optional

from app.services.runtime_dependencies import get_db_session
from app.models.agents.agent_studio import (
    AgentFlowDebugEvent,
    AgentFlowDebugSession,
    AgentFlowDefinition,
    AgentFlowVersion,
)
from app.services.agents.studio.flow_compiler import FlowCompiler
from app.services.agents.studio.flow_validator import FlowValidator
from app.services.agents.studio.dry_run_runner import AgentGraphDryRunRunner
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
    permissions: List[str] = Field(default_factory=list)
    required_capabilities: List[str] = Field(default_factory=list)
    risk_level: str = "low"

class FlowResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: Any

class ExplainResponse(BaseModel):
    summary: str
    nodes_explained: List[Dict[str, str]]
    estimated_cost: float

class DryRunResponse(BaseModel):
    status: str
    trace: List[Dict[str, Any]]
    final_output: Any
    side_effects_prevented: List[str]

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
        graph_json=payload.graph_json,
        permissions=payload.permissions,
        required_capabilities=payload.required_capabilities,
        risk_level=payload.risk_level
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

@router.post("/flows/{id}/explain", response_model=ExplainResponse)
async def explain_flow(id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    stmt = select(AgentFlowVersion).where(AgentFlowVersion.flow_id == id, AgentFlowVersion.is_active == True)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Active flow version not found")

    nodes = version.graph_json.get("nodes", [])
    nodes_explained = []
    estimated_cost = 0.0

    for node in nodes:
        ntype = node.get("node_type", "unknown")
        nname = node.get("data", {}).get("label", ntype)
        desc = f"Executes logic for {ntype}."
        if ntype == "model_call":
            desc = "Calls LLM model. Estimated cost: ~$0.01 per execution."
            estimated_cost += 0.01
        elif ntype == "tool_call":
             desc = f"Invokes tool: {node.get('config', {}).get('tool_name', 'unknown')}. May have side effects."
        
        nodes_explained.append({
            "node_id": str(node.get("id")),
            "name": nname,
            "description": desc
        })

    return ExplainResponse(
        summary=f"This workflow contains {len(nodes)} nodes with a risk level of {version.risk_level}.",
        nodes_explained=nodes_explained,
        estimated_cost=estimated_cost
    )

@router.post("/flows/{id}/dry-run", response_model=DryRunResponse)
async def dry_run_flow(id: uuid.UUID, input_data: Dict[str, Any] = None, db: AsyncSession = Depends(get_db_session)):
    stmt = select(AgentFlowVersion).where(AgentFlowVersion.flow_id == id, AgentFlowVersion.is_active == True)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Active flow version not found")

    # Preliminary permission check (baseline)
    nodes = version.graph_json.get("nodes", [])
    for node in nodes:
        if node.get("node_type") == "memory_write" and "memory:write" not in version.permissions:
             raise HTTPException(status_code=403, detail=f"Node {node.get('id')} blocked: missing memory:write permission.")

    # Real dry-run execution
    runner = AgentGraphDryRunRunner(db)
    result = await runner.run_dry_run(version.graph_json, global_input=input_data)
    
    return DryRunResponse(**result)

@router.get("/flows/runs/{run_id}/trace")
async def get_flow_trace(run_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    # Redirects to existing debug trace logic
    return await get_debug_session(run_id, db)
async def get_debug_session(run_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    stmt = select(AgentFlowDebugSession).where(AgentFlowDebugSession.run_id == run_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
         raise HTTPException(status_code=404, detail="Debug session not found")
         
    stmt_e = select(AgentFlowDebugEvent).where(AgentFlowDebugEvent.session_id == session.id).order_by(AgentFlowDebugEvent.created_at.asc())
    res_e = await db.execute(stmt_e)
    events = res_e.scalars().all()
    
    return {"session": session, "events": events}
