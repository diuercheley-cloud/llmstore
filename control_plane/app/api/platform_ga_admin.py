# Owner: platform-ops
from app.services.platform.ga_readiness import GAReadinessService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/admin/platform", tags=["Platform GA Readiness"])

def get_ga_readiness_service():
    return GAReadinessService()

@router.get("/ga-readiness")
def get_ga_readiness(service: GAReadinessService = Depends(get_ga_readiness_service)):
    """
    Returns the current GA readiness maturity level and score.
    """
    current_state = service.collect_current_state()
    result = service.evaluate_readiness(current_state)
    return {
        **result,
        "current_state": current_state,
    }

@router.get("/maturity-report")
def get_maturity_report(service: GAReadinessService = Depends(get_ga_readiness_service)):
    """
    Generates and returns the maturity report artifact.
    """
    current_state = service.collect_current_state()
    result = service.generate_report(current_state)
    return {
        "message": "Report generated successfully at artifacts/platform/ga-readiness.md",
        "report_summary": result
    }
