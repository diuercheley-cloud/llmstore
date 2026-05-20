from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.db.session import get_db_session
from app.services.compliance_readiness import ComplianceReadinessService
from app.services.compliance_control_mapper import ComplianceControlMapperService
from app.services.compliance_evidence_collector import ComplianceEvidenceCollectorService
from app.services.isms_manager import ISMSManagerService
from app.services.soc2_control_operations import SOC2ControlOperationsService
from app.services.compliance_gap_analysis import ComplianceGapAnalysisService
from pydantic import BaseModel

router = APIRouter(prefix="/admin/compliance", tags=["compliance"])

@router.get("/frameworks")
async def list_frameworks(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ComplianceReadinessService(db)
    return await service.list_frameworks()

@router.get("/readiness-report/{framework_id}")
async def get_report(
    framework_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ComplianceReadinessService(db)
    try:
        return await service.get_readiness_report(framework_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/evidence/collect")
async def collect_evidence(
    control_id: str,
    name: str,
    description: str,
    content: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ComplianceReadinessService(db)
    try:
        return await service.collect_evidence(control_id, name, description, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/control-map")
async def get_control_map(
    framework: Optional[str] = None,
    admin: Any = Depends(get_current_admin)
):
    service = ComplianceControlMapperService()
    return service.list_controls(framework)

@router.get("/control-map/{framework}/{control_id}")
async def get_control_detail(
    framework: str,
    control_id: str,
    admin: Any = Depends(get_current_admin)
):
    service = ComplianceControlMapperService()
    control = service.get_control(framework, control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control mapping not found")
    return control

@router.post("/evidence/collect-all")
async def collect_all_evidence(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ComplianceEvidenceCollectorService(db)
    result = await service.collect_all()
    await service.generate_package()
    return result

@router.get("/evidence/latest")
async def get_latest_evidence_index(
    admin: Any = Depends(get_current_admin)
):
    index_path = "artifacts/compliance/latest/evidence-index.json"
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="No evidence index found. Run collection first.")
    with open(index_path, "r") as f:
        return json.load(f)

@router.get("/isms/status")
async def get_isms_status(
    admin: Any = Depends(get_current_admin)
):
    service = ISMSManagerService()
    return service.get_status()

@router.get("/isms/policies")
async def list_isms_policies(
    admin: Any = Depends(get_current_admin)
):
    service = ISMSManagerService()
    return service.list_policies()

@router.get("/isms/risk-register")
async def get_risk_register(
    admin: Any = Depends(get_current_admin)
):
    service = ISMSManagerService()
    return service.get_risk_register()

@router.post("/soc2/access-review")
async def create_access_review(
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = SOC2ControlOperationsService(db)
    try:
        return await service.create_access_review(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/soc2/access-reviews")
async def list_access_reviews(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = SOC2ControlOperationsService(db)
    return await service.list_access_reviews()

@router.post("/soc2/exceptions")
async def create_exception(
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = SOC2ControlOperationsService(db)
    try:
        return await service.create_exception(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/gap-analysis")
async def run_gap_analysis(
    admin: Any = Depends(get_current_admin)
):
    service = ComplianceGapAnalysisService()
    return service.generate_full_analysis()
