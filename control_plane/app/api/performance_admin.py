# Owner: platform-ops
from typing import Any, List, Optional

from app.api.dependencies import get_current_admin
from app.services.runtime_dependencies import get_db_session
from app.services.runtime_tuning import RuntimeTuningService
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/performance", tags=["performance"])

class BenchmarkResponse(BaseModel):
    id: str
    model_id: str
    tokens_per_sec: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    queue_wait_ms: float
    gpu_memory_pressure: float
    cpu_usage: float
    cache_hit_ratio: float
    fallback_rate: float
    cost_per_1k_tokens: float
    error_rate: float
    timestamp: Any

class RecommendationResponse(BaseModel):
    id: str
    title: str
    description: str
    action_type: str
    impact: str
    priority: str
    suggested_config: dict
    status: str

class ProfileResponse(BaseModel):
    name: str
    description: str
    config: dict
    is_active: bool

@router.post("/benchmark", response_model=BenchmarkResponse)
async def run_benchmark(
    model_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = RuntimeTuningService(db)
    return await service.run_benchmark(model_id)

@router.get("/benchmarks", response_model=List[BenchmarkResponse])
async def list_benchmarks(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = RuntimeTuningService(db)
    return await service.list_benchmarks()

@router.get("/recommendations", response_model=List[RecommendationResponse])
async def list_recommendations(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = RuntimeTuningService(db)
    return await service.get_recommendations()

@router.post("/apply-profile")
async def apply_profile(
    profile_name: str,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = RuntimeTuningService(db)
    try:
        return await service.apply_profile(profile_name, operator_id=admin.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/current-profile", response_model=Optional[ProfileResponse])
async def get_current_profile(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = RuntimeTuningService(db)
    return await service.get_current_profile()

@router.get("/profiles", response_model=List[ProfileResponse])
async def list_profiles(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = RuntimeTuningService(db)
    return await service.list_profiles()

@router.post("/seed-profiles")
async def seed_profiles(
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin)
):
    service = RuntimeTuningService(db)
    await service.seed_default_profiles()
    return {"status": "success"}
