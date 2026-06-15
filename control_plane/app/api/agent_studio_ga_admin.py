import logging
import uuid
from typing import Any

from app.api.deps import get_current_user, get_db
from app.models.agents.agent_studio import AgentFlowDefinition, AgentFlowVersion
from app.services.agents.studio.flow_compiler import FlowCompiler
from app.services.agents.studio.flow_runtime_adapter import FlowRuntimeAdapter
from app.services.agents.studio.flow_validator import FlowValidator
from app.services.agents.studio.flow_versioning import FlowVersioningService
from app.services.agents.studio.studio_workflow_bridge import StudioWorkflowBridge
from app.services.agents.studio.template_gallery import TemplateGalleryService
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/agents/studio", tags=["Agent Studio GA"])


class CreateFlowRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class SaveVersionRequest(BaseModel):
    graph: dict
    label: str = Field(..., min_length=1)
    make_active: bool = False


def get_tenant_id(user) -> str:
    tenant_id = getattr(user, "tenant_id", None) or getattr(user, "id", None) or "default"
    return str(tenant_id)


@router.post("/flows")
async def create_flow(
    req: CreateFlowRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = get_tenant_id(user)
    service = FlowVersioningService(db)
    return await service.create_flow(tenant_id, req.name, req.description)


@router.post("/flows/{flow_id}/versions")
async def save_flow_version(
    flow_id: uuid.UUID,
    req: SaveVersionRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = get_tenant_id(user)
    flow = await db.get(AgentFlowDefinition, flow_id)
    if not flow or flow.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Flow not found")
    service = FlowVersioningService(db)
    return await service.save_version(flow_id, req.graph, req.label, req.make_active)


@router.post("/versions/{version_id}/validate")
async def validate_flow_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = get_tenant_id(user)
    version = await db.get(AgentFlowVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    flow = await db.get(AgentFlowDefinition, version.flow_id)
    if not flow or flow.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Version not found")
    validator = FlowValidator()
    return validator.validate(version)


@router.post("/versions/{version_id}/compile")
async def compile_flow_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = get_tenant_id(user)
    version = await db.get(AgentFlowVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    flow = await db.get(AgentFlowDefinition, version.flow_id)
    if not flow or flow.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Version not found")
    compiler = FlowCompiler()
    return compiler.compile(version)


@router.post("/versions/{version_id}/deploy-real")
async def deploy_real_flow_version(
    version_id: uuid.UUID,
    input_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = get_tenant_id(user)
    version = await db.get(AgentFlowVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    flow = await db.get(AgentFlowDefinition, version.flow_id)
    if not flow or flow.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Version not found")
    adapter = FlowRuntimeAdapter(db)
    return await adapter.deploy_real(version_id, input_data)


@router.get("/templates")
async def list_templates():
    gallery = TemplateGalleryService()
    return {"templates": gallery.list_templates()}


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    gallery = TemplateGalleryService()
    template = gallery.get_template_details(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/flows/{flow_id}/deploy")
async def deploy_flow(
    flow_id: uuid.UUID,
    input_data: dict[str, Any] | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = get_tenant_id(user)
    bridge = StudioWorkflowBridge(db)
    try:
        run = await bridge.deploy_flow_as_workflow(flow_id, tenant_id, input_data)
        return {"run_id": str(run.id), "status": run.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/flows/{flow_id}/versions/{version_id}/dag")
async def compile_flow_to_dag(
    flow_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    tenant_id = get_tenant_id(user)
    bridge = StudioWorkflowBridge(db)
    try:
        return await bridge.compile_flow_to_dag(version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
