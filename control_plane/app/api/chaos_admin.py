# Owner: platform-ops
from typing import Any

from app.api.dependencies import get_current_admin
from app.db.session import get_db_session
from app.services.chaos_engineering import ChaosEngineeringService
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/chaos", tags=["chaos"])

class ChaosRunCreate(BaseModel):
    experiment_id: str

class ChaosStatusResponse(BaseModel):
    enabled: bool
    environment: str
    allow_production: bool
    blocked_in_production: bool
    operational: bool
    state: str
    reason: str | None = None

@router.get("/experiments")
async def list_experiments(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ChaosEngineeringService(db)
    return await service.list_experiments()

@router.get("/status", response_model=ChaosStatusResponse)
async def get_status(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ChaosEngineeringService(db)
    return await service.get_status()

@router.get("/runs")
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ChaosEngineeringService(db)
    return await service.list_runs(limit=limit)

@router.post("/runs")
async def create_run(
    data: ChaosRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ChaosEngineeringService(db)
    run = await service.create_run(data.experiment_id, operator_id=admin.id)
    background_tasks.add_task(service.start_run, run.id)
    return run

@router.get("/runs/{id}/report")
async def get_report(
    id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ChaosEngineeringService(db)
    report = await service.get_report(id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found for this run")
    return report

@router.post("/runs/{id}/abort")
async def abort_run(
    id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = ChaosEngineeringService(db)
    await service.abort_run(id)
    return {"status": "abort_requested"}
