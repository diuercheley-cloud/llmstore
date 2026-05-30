# Owner: agent-platform
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.services.prompts.prompt_registry import PromptRegistry
from app.services.prompts.prompt_versioning import PromptVersioningService
from app.services.prompts.prompt_playground import PromptPlayground
from app.services.prompts.prompt_ab_testing import PromptABTestingService

router = APIRouter()

@router.post("/")
async def create_template(
    name: str,
    description: Optional[str] = None,
    variable_schema: Optional[Dict] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    registry = PromptRegistry(db)
    template = await registry.create_template(current_user.tenant_id, name, description, variable_schema)
    await db.commit()
    return template

@router.get("/")
async def list_templates(
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    registry = PromptRegistry(db)
    return await registry.list_templates(current_user.tenant_id)

@router.post("/{template_id}/versions")
async def create_version(
    template_id: uuid.UUID,
    content: str,
    version_tag: str,
    provider_settings: Optional[Dict] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    registry = PromptRegistry(db)
    version = await registry.create_version(template_id, content, current_user.email, version_tag, provider_settings)
    await db.commit()
    return version

@router.post("/{template_id}/playground")
async def run_playground(
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    variables: Dict[str, Any],
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    playground = PromptPlayground(db)
    run = await playground.run_playground(version_id, variables, current_user.email)
    await db.commit()
    return run

@router.post("/{template_id}/experiments")
async def create_experiment(
    template_id: uuid.UUID,
    version_a_id: uuid.UUID,
    version_b_id: uuid.UUID,
    name: str,
    split: float = 0.5,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    ab_service = PromptABTestingService(db)
    exp = await ab_service.create_experiment(current_user.tenant_id, template_id, version_a_id, version_b_id, name, split)
    await db.commit()
    return exp

@router.post("/{template_id}/versions/{version_id}/promote")
async def promote_version(
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    target_status: str, # staging, production
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_admin_user)
):
    versioning = PromptVersioningService(db)
    if target_status == "staging":
        success = await versioning.promote_to_staging(version_id)
    elif target_status == "production":
        success = await versioning.promote_to_production(version_id)
        if success:
            registry = PromptRegistry(db)
            await registry.set_active_version(template_id, version_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid target status")
    
    if not success:
        raise HTTPException(status_code=400, detail="Promotion failed (check security or status constraints)")
    
    await db.commit()
    return {"status": "promoted", "target": target_status}
