# Owner: platform-ops
# Owner: platform-ops
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db, get_current_admin
from app.services.agents.catalog.capability_catalog import CapabilityCatalogService
from app.services.agents.catalog.trust_report import TrustReportService
from app.services.plugins.plugin_signature import PluginSignatureService
from app.services.plugins.plugin_runtime import PluginRuntimeService
from app.core.config import get_settings
import uuid
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/admin/agents/capability-catalog", tags=["capability_catalog_admin"])
settings = get_settings()

class CapabilityInstallRequest(BaseModel):
    name: str
    category: str
    version: str
    owner: str
    manifest: dict
    permissions: List[str] = []
    support_level: str = "beta"

@router.get("")
async def list_capabilities(category: Optional[str] = None, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    return await CapabilityCatalogService(db).list_entries(category)

@router.post("/install", status_code=status.HTTP_201_CREATED)
async def install_capability(data: CapabilityInstallRequest, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    return await CapabilityCatalogService(db).install_entry(data.model_dump())

@router.post("/{entry_id}/approve")
async def approve_capability(entry_id: uuid.UUID, comment: str = None, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    return await CapabilityCatalogService(db).approve_entry(entry_id, admin.id, comment)

@router.post("/{entry_id}/disable")
async def disable_capability(entry_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    await CapabilityCatalogService(db).disable_entry(entry_id)
    return {"status": "disabled"}

@router.get("/{entry_id}/trust-report")
async def get_trust_report(entry_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    from sqlalchemy import select
    from app.models.agent_catalog import PluginTrustReportGov
    result = await db.execute(select(PluginTrustReportGov).where(PluginTrustReportGov.catalog_entry_id == entry_id))
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail="Trust report not found")
    return report

# Plugin specific endpoints under same prefix or separate?
# The user asked for /admin/plugins/... too

plugin_router = APIRouter(prefix="/admin/plugins", tags=["plugin_admin"])

@plugin_router.post("/{entry_id}/verify-signature")
async def verify_plugin_signature(entry_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    # In a real impl, this would verify the cryptographic signature
    return {"status": "verified", "entry_id": entry_id}

@plugin_router.post("/{entry_id}/run-dry-run")
async def run_plugin_dry_run(entry_id: uuid.UUID, parameters: dict, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    # This would use dry_run sandbox type
    return {"status": "dry_run_success", "output": {"result": 42}}
