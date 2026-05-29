# Owner: agent-platform
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.agents.studio.flow_versioning import FlowVersioningService
from app.services.agents.studio.flow_validator import FlowValidator
from app.services.agents.studio.flow_compiler import FlowCompiler
from app.services.agents.studio.flow_runtime_adapter import FlowRuntimeAdapter
from app.models.agent_studio import AgentFlowVersion

router = APIRouter(prefix="/admin/agents/studio", tags=["Agent Studio GA"])

@router.post("/flows")
async def create_flow(
    config: Dict[str, Any],
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    service = FlowVersioningService(db)
    return await service.create_flow(tenant_id, config["name"], config.get("description"))

@router.post("/flows/{flow_id}/versions")
async def save_flow_version(
    flow_id: uuid.UUID,
    version_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    service = FlowVersioningService(db)
    return await service.save_version(
        flow_id, 
        version_data["graph"], 
        version_data["label"],
        version_data.get("make_active", False)
    )

@router.post("/versions/{version_id}/validate")
async def validate_flow_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    version = await db.get(AgentFlowVersion, version_id)
    if not version: raise HTTPException(status_code=404, detail="Version not found")
    validator = FlowValidator()
    return validator.validate(version)

@router.post("/versions/{version_id}/compile")
async def compile_flow_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    version = await db.get(AgentFlowVersion, version_id)
    if not version: raise HTTPException(status_code=404, detail="Version not found")
    compiler = FlowCompiler()
    return compiler.compile(version)

@router.post("/versions/{version_id}/dry-run")
async def dry_run_flow_version(
    version_id: uuid.UUID,
    input_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    adapter = FlowRuntimeAdapter(db)
    return await adapter.dry_run(version_id, input_data)
