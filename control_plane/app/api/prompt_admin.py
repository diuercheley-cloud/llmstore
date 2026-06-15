# Owner: agent-platform
import uuid
from typing import Any

from app.api import deps
from app.core.config import get_settings
from app.services.prompts.prompt_ab_testing import PromptABTestingService
from app.services.prompts.prompt_playground import PromptPlayground
from app.services.prompts.prompt_registry import PromptRegistry
from app.services.prompts.prompt_template_playground import PromptTemplatePlaygroundService
from app.services.prompts.prompt_template_registry import PromptTemplateRegistryService
from app.services.prompts.prompt_template_renderer import PromptTemplateRenderer
from app.services.prompts.prompt_template_validator import PromptTemplateValidator
from app.services.prompts.prompt_template_versioning import PromptTemplateVersioningService
from app.services.prompts.prompt_versioning import PromptVersioningService
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/admin/prompts", tags=["prompt-management"])


def _require_templates_enabled():
    settings = get_settings()
    if not settings.prompt_templates_enabled:
        raise HTTPException(status_code=403, detail="Prompt templates are disabled")


def _require_playground_enabled():
    settings = get_settings()
    if not settings.prompt_template_playground_enabled:
        raise HTTPException(status_code=403, detail="Prompt template playground is disabled")


@router.post("/")
async def create_template(
    name: str = Body(...),
    description: str | None = Body(None),
    variable_schema: dict | None = Body(None),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
):
    registry = PromptRegistry(db)
    template = await registry.create_template(
        current_user.tenant_id, name, description, variable_schema
    )
    await db.commit()
    return template


@router.get("/")
async def list_templates(
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
):
    registry = PromptRegistry(db)
    return await registry.list_templates(current_user.tenant_id)


@router.post("/{template_id}/versions")
async def create_version(
    template_id: uuid.UUID,
    content: str = Body(...),
    version_tag: str = Body(...),
    provider_settings: dict | None = Body(None),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
):
    registry = PromptRegistry(db)
    version = await registry.create_version(
        template_id, content, current_user.email, version_tag, provider_settings
    )
    await db.commit()
    return version


@router.post("/{template_id}/playground")
async def run_playground(
    template_id: uuid.UUID,
    version_id: uuid.UUID = Body(...),
    variables: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
):
    _require_playground_enabled()
    playground = PromptPlayground(db)
    run = await playground.run_playground(version_id, variables, current_user.email)
    await db.commit()
    return run


@router.post("/{template_id}/experiments")
async def create_experiment(
    template_id: uuid.UUID,
    version_a_id: uuid.UUID = Body(...),
    version_b_id: uuid.UUID = Body(...),
    name: str = Body(...),
    split: float = Body(0.5),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
):
    ab_service = PromptABTestingService(db)
    exp = await ab_service.create_experiment(
        current_user.tenant_id, template_id, version_a_id, version_b_id, name, split
    )
    await db.commit()
    return exp


@router.post("/{template_id}/versions/{version_id}/promote")
async def promote_version(
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    target_status: str = Body(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
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
        raise HTTPException(
            status_code=400, detail="Promotion failed (check security or status constraints)"
        )

    await db.commit()
    return {"status": "promoted", "target": target_status}


# --- New Template Engine Endpoints (v2) ---


@router.post("/templates")
async def create_prompt_template(
    name: str = Body(...),
    description: str | None = Body(None),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
):
    _require_templates_enabled()
    svc = PromptTemplateRegistryService(db)
    template = await svc.create_template(
        tenant_id=current_user.tenant_id,
        name=name,
        description=description,
    )

    vars_data = []
    if template:
        vars_data = await svc.get_declared_variables(template.id)

    await db.commit()
    return {
        "id": str(template.id),
        "name": template.name,
        "description": template.description,
        "variables": [
            {
                "name": v.name,
                "type": v.var_type,
                "required": v.required,
                "default": v.default,
                "description": v.description,
            }
            for v in vars_data
        ],
        "created_at": template.created_at.isoformat(),
    }


@router.get("/templates")
async def list_prompt_templates(
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
) -> list[dict[str, Any]]:
    _require_templates_enabled()
    svc = PromptTemplateRegistryService(db)
    templates = await svc.list_templates(tenant_id=current_user.tenant_id)
    result = []
    for t in templates:
        vars_data = await svc.get_declared_variables(t.id)
        result.append(
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "active_version_id": str(t.active_version_id) if t.active_version_id else None,
                "variables_count": len(vars_data),
                "variables": [
                    {
                        "name": v.name,
                        "type": v.var_type,
                        "required": v.required,
                        "default": v.default,
                        "description": v.description,
                    }
                    for v in vars_data
                ],
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
            }
        )
    return result


@router.post("/templates/{template_id}/variables")
async def declare_template_variable(
    template_id: uuid.UUID,
    name: str = Body(...),
    var_type: str = Body("string"),
    required: bool = Body(True),
    default: str | None = Body(None),
    description: str | None = Body(None),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
) -> dict[str, Any]:
    _require_templates_enabled()
    svc = PromptTemplateRegistryService(db)
    try:
        var = await svc.declare_variable(
            template_id=template_id,
            name=name,
            var_type=var_type,
            required=required,
            default=default,
            description=description,
        )
        await db.commit()
        return {
            "id": str(var.id),
            "template_id": str(template_id),
            "name": var.name,
            "type": var.var_type,
            "required": var.required,
            "default": var.default,
            "description": var.description,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/templates/{template_id}/versions")
async def create_template_version(
    template_id: uuid.UUID,
    content: str = Body(...),
    version_tag: str = Body(...),
    provider_settings: dict[str, Any] | None = Body(None),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
) -> dict[str, Any]:
    _require_templates_enabled()
    svc = PromptTemplateRegistryService(db)
    try:
        version = await svc.create_version(
            template_id=template_id,
            content=content,
            created_by=current_user.email,
            version_tag=version_tag,
            provider_settings=provider_settings,
        )
        await db.commit()
        return {
            "id": str(version.id),
            "template_id": str(template_id),
            "version_tag": version.version_tag,
            "status": version.status,
            "content_preview": version.content[:200],
            "created_by": version.created_by,
            "created_at": version.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/templates/{template_id}/render")
async def render_template(
    template_id: uuid.UUID,
    version_id: uuid.UUID = Body(...),
    variables: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
) -> dict[str, Any]:
    _require_templates_enabled()
    svc = PromptTemplateRegistryService(db)
    declared = await svc.get_declared_variables(template_id)

    declared_list = [
        {
            "name": v.name,
            "type": v.var_type,
            "required": v.required,
            "default": v.default,
            "description": v.description,
        }
        for v in declared
    ]

    playground = PromptTemplatePlaygroundService(db)
    try:
        result = await playground.render_only(
            version_id=version_id,
            variables=variables,
            declared_vars=declared_list,
        )

        template = await svc.get_template(template_id, current_user.tenant_id)
        if template:
            await svc.record_render_event(
                template_id=template_id,
                version_id=version_id,
                tenant_id=current_user.tenant_id,
                variables_hash=result["variables_hash"],
                output_hash=result["output_hash"],
                rendered_content_hash=result["rendered_content_hash"],
            )
            await db.commit()

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/templates/{template_id}/playground")
async def template_playground(
    template_id: uuid.UUID,
    version_id: uuid.UUID = Body(...),
    variables: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
) -> dict[str, Any]:
    _require_templates_enabled()
    _require_playground_enabled()

    svc = PromptTemplateRegistryService(db)
    declared = await svc.get_declared_variables(template_id)
    declared_list = [
        {
            "name": v.name,
            "type": v.var_type,
            "required": v.required,
            "default": v.default,
            "description": v.description,
        }
        for v in declared
    ]

    playground = PromptTemplatePlaygroundService(db)
    try:
        run = await playground.run_playground(
            version_id=version_id,
            variables=variables,
            created_by=current_user.email,
            declared_vars=declared_list,
        )
        await db.commit()
        return {
            "id": str(run.id),
            "version_id": str(version_id),
            "rendered": run.output,
            "latency_ms": run.latency_ms,
            "token_usage": run.token_usage,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/templates/{template_id}/versions/{version_id}/promote")
async def promote_template_version(
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    target_status: str = Body(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
) -> dict[str, Any]:
    _require_templates_enabled()
    versioning = PromptTemplateVersioningService(db)

    try:
        if target_status == "staging":
            success = await versioning.promote_to_staging(version_id)
        elif target_status == "production":
            success = await versioning.promote_to_production(version_id)
            if success:
                svc = PromptTemplateRegistryService(db)
                template = await svc.get_template(template_id, current_user.tenant_id)
                if template:
                    await svc.set_active_version(template_id, version_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid target status")

        if not success:
            raise HTTPException(
                status_code=400, detail="Promotion failed (check validation or status constraints)"
            )

        await db.commit()
        return {"status": "promoted", "target": target_status, "version_id": str(version_id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/templates/{template_id}/rollback")
async def rollback_template(
    template_id: uuid.UUID,
    to_version_id: uuid.UUID = Body(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
) -> dict[str, Any]:
    _require_templates_enabled()
    versioning = PromptTemplateVersioningService(db)
    success = await versioning.rollback(template_id, to_version_id)
    if not success:
        raise HTTPException(status_code=400, detail="Rollback failed")
    await db.commit()
    return {
        "status": "rolled_back",
        "template_id": str(template_id),
        "to_version_id": str(to_version_id),
    }


@router.post("/validate")
async def validate_template_content(
    content: str = Body(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
) -> dict[str, Any]:
    _require_templates_enabled()
    validator = PromptTemplateValidator(  # type: ignore[call-arg]
        PromptTemplateRenderer()  # type: ignore[arg-type]
    )
    result = validator.validate_template_content(content)
    return result.to_dict()


@router.get("/templates/{template_id}/render-events")
async def list_render_events(
    template_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(deps.get_db),
    current_user=Depends(deps.get_current_admin_user),
) -> list[dict[str, Any]]:
    _require_templates_enabled()
    svc = PromptTemplateRegistryService(db)
    events = await svc.count_render_events(template_id, limit=limit)
    return [
        {
            "id": str(e.id),
            "version_id": str(e.version_id),
            "variables_hash": e.variables_hash,
            "output_hash": e.output_hash,
            "agent_run_id": str(e.agent_run_id) if e.agent_run_id else None,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
