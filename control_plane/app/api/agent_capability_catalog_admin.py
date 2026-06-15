# Owner: platform-ops
# Owner: platform-ops
import uuid

from app.api.dependencies import get_current_admin, get_db
from app.core.config import get_settings
from app.services.agents.catalog.capability_catalog import CapabilityCatalogService
from app.services.plugins.plugin_runtime import PluginRuntimeService
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/capability-catalog", tags=["capability_catalog_admin"])
settings = get_settings()


class CapabilityInstallRequest(BaseModel):
    name: str
    category: str
    version: str
    owner: str
    manifest: dict
    permissions: list[str] = []
    support_level: str = "beta"


@router.get("")
async def list_capabilities(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    return await CapabilityCatalogService(db).list_entries(category)


@router.post("/install", status_code=status.HTTP_201_CREATED)
async def install_capability(
    data: CapabilityInstallRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    return await CapabilityCatalogService(db).install_entry(data.model_dump())


@router.post("/{entry_id}/approve")
async def approve_capability(
    entry_id: uuid.UUID,
    comment: str = None,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    return await CapabilityCatalogService(db).approve_entry(entry_id, admin.id, comment)


@router.post("/{entry_id}/disable")
async def disable_capability(
    entry_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    await CapabilityCatalogService(db).disable_entry(entry_id)
    return {"status": "disabled"}


@router.get("/{entry_id}/trust-report")
async def get_trust_report(
    entry_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    from app.models.agents.agent_catalog import PluginTrustReportGov
    from sqlalchemy import select

    result = await db.execute(
        select(PluginTrustReportGov).where(PluginTrustReportGov.catalog_entry_id == entry_id)
    )
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Trust report not found")
    return report


# Plugin specific endpoints under same prefix or separate?
# The user asked for /admin/plugins/... too

plugin_router = APIRouter(prefix="/admin/plugins", tags=["plugin_admin"])


class DryRunRequest(BaseModel):
    code: str
    parameters: dict


class ExecuteRequest(BaseModel):
    code: str
    parameters: dict
    tenant_id: str


@plugin_router.post("/{id}/verify")
async def verify_plugin(
    id: uuid.UUID, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    service = PluginRuntimeService(db)
    return await service.verify_plugin(id)


@plugin_router.post("/{id}/dry-run")
async def dry_run_plugin(
    id: uuid.UUID,
    data: DryRunRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginRuntimeService(db)
    return await service.dry_run_plugin(id, data.code, data.parameters)


@plugin_router.post("/{id}/execute")
async def execute_plugin(
    id: uuid.UUID,
    data: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginRuntimeService(db)
    result = await service.run_plugin(id, data.code, data.parameters, data.tenant_id)
    return {"status": "success", "result": result}


@plugin_router.get("/{id}/trust-report")
async def get_trust_report_endpoint(
    id: uuid.UUID, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    service = PluginRuntimeService(db)
    return await service.get_trust_report(id)
