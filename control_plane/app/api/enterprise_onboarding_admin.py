# Owner: platform-ops
from typing import Any, List, Optional

from app.api.dependencies import get_current_admin
from app.services.runtime_dependencies import get_db_session
from app.services.enterprise_onboarding import EnterpriseOnboardingService
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/enterprise/onboarding", tags=["enterprise_onboarding"])

class ProjectCreate(BaseModel):
    customer_name: str
    contact_email: str
    project_name: str
    tier: str = "pilot"

class ProjectResponse(BaseModel):
    id: str
    name: str
    status: str
    start_date: Any
    customer_id: str

class TaskUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = EnterpriseOnboardingService(db)
    customer = await service.create_customer(data.customer_name, data.contact_email, data.tier)
    project = await service.create_project(customer.id, data.project_name)
    return project

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = EnterpriseOnboardingService(db)
    return await service.list_projects()

@router.get("/projects/{id}")
async def get_project(
    id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = EnterpriseOnboardingService(db)
    project = await service.get_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.patch("/tasks/{id}")
async def update_task(
    id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = EnterpriseOnboardingService(db)
    try:
        return await service.update_task_status(id, data.status, data.notes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/projects/{id}/handover-report")
async def generate_handover_report(
    id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = EnterpriseOnboardingService(db)
    try:
        return await service.generate_handover_report(id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
