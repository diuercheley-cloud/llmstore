# Owner: agent-platform
import uuid

from app.core.config import get_settings
from app.services.runtime_dependencies import get_db
from app.services.agents.sab.sab_exporter import SABExporter
from app.services.agents.sab.sab_importer import SABImporter
from app.services.agents.sab.sab_manifest import AgentSABManifest
from app.services.agents.sab.sab_verifier import SABVerifier
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/sab", tags=["Standardized Agent Bundle (SAB)"])

@router.post("/export/{agent_id}")
async def export_agent_sab(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    settings = get_settings()
    if not settings.agent_sab_export_enabled:
        raise HTTPException(status_code=403, detail="SAB Export is disabled.")
    
    service = SABExporter(db)
    try:
        return await service.export_agent(agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/import")
async def import_agent_sab(
    manifest: AgentSABManifest,
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    settings = get_settings()
    if not settings.agent_sab_import_enabled:
        raise HTTPException(status_code=403, detail="SAB Import is disabled.")
    
    service = SABImporter(db)
    try:
        return await service.import_agent(manifest, tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify")
async def verify_agent_sab(
    manifest: AgentSABManifest
):
    verifier = SABVerifier()
    is_valid, reason = verifier.verify(manifest)
    return {"is_valid": is_valid, "reason": reason}
