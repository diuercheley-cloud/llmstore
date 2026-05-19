from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_db, require_admin
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.security.attestation_service import NodeAttestationService
from app.services.security.pki_service import PKIService
from app.core.config import get_settings

router = APIRouter(prefix="/admin/security", tags=["security-pki-attestation"])

@router.get("/attestation/report")
async def get_attestation_report(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Generate an attestation report for this node.
    """
    try:
        service = NodeAttestationService(db)
        report = await service.generate_report()
        return report.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/attestation/verify")
async def verify_attestation_report(
    report: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Verify an attestation report.
    """
    service = NodeAttestationService(db)
    try:
        is_valid = await service.verify_report(report)
        return {"verified": is_valid, "mode": service.settings.attestation_mode}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/pki/init")
async def init_pki(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Initialize the local PKI CA.
    """
    settings = get_settings()
    if not settings.pki_enabled:
        raise HTTPException(status_code=400, detail="PKI is not enabled")
    
    service = PKIService(db)
    try:
        await service.initialize_ca()
        return {"status": "success", "message": "PKI initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
