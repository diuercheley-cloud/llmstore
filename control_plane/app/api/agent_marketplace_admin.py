import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import require_admin, get_db_session
from app.services.agents.agent_marketplace import AgentMarketplaceService
from app.services.agents.agent_bundle_verifier import AgentBundleVerifierService
from app.services.agents.agent_supply_chain import AgentSupplyChainService

router = APIRouter(prefix="/admin/agent-marketplace", tags=["agent-marketplace"])

@router.post("/bundles/verify")
async def verify_bundle(
    file: UploadFile = File(...),
    version_id: uuid.UUID = Body(...),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentBundleVerifierService(db)
    content = await file.read()
    result = await service.verify_bundle(version_id, content)
    return result

@router.post("/bundles/{id}/review")
async def review_publication(
    id: uuid.UUID, # version_id
    status: str = Body(...),
    notes: Optional[str] = Body(None),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentSupplyChainService(db)
    reviewer = getattr(admin, "email", "admin")
    # This is a bit simplified, usually we'd have a review_id
    # For now let's just use version_id to find or create a review
    review = await service.submit_for_review(id, reviewer)
    if status == "approved":
        await service.approve_publication(review.id, notes or "Approved via API")
    
    return {"id": str(review.id), "status": status}

@router.post("/bundles/{id}/publish")
async def publish_bundle(
    id: uuid.UUID, # version_id
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    # Check if approved
    return {"status": "published"}

@router.get("")
async def list_marketplace(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> List[Dict[str, Any]]:
    service = AgentMarketplaceService(db)
    entries = await service.list_marketplace()
    return [
        {
            "id": str(e.id),
            "name": e.name,
            "description": e.description,
            "author": e.author,
            "category": e.category,
            "official": e.official,
            "avg_rating": e.avg_rating,
        }
        for e in entries
    ]

@router.post("/install")
async def install_bundle(
    file: UploadFile = File(...),
    tenant_id: str = Body("default"),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentMarketplaceService(db)
    content = await file.read()
    try:
        install = await service.install_bundle(tenant_id, content, file.filename or "bundle.json")
        return {"id": str(install.id), "status": install.status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{install_id}/enable")
async def enable_bundle(
    install_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentMarketplaceService(db)
    await service.enable_install(install_id)
    return {"status": "enabled"}

@router.post("/{install_id}/disable")
async def disable_bundle(
    install_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentMarketplaceService(db)
    await service.disable_install(install_id)
    return {"status": "disabled"}

@router.get("/versions/{version_id}/trust-report")
async def get_trust_report(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    service = AgentMarketplaceService(db)
    report = await service.get_trust_report(version_id)
    if not report:
        raise HTTPException(status_code=404, detail="Trust report not found")
    
    return {
        "version_id": str(report.version_id),
        "trust_score": report.trust_score,
        "is_signed": report.is_signed,
        "signer": report.signer_identity,
        "vulnerabilities": report.vulnerabilities,
        "details": report.report_details,
    }
