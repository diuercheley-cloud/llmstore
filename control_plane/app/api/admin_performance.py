from typing import List

from app.api.dependencies import get_current_admin
from app.services.runtime_dependencies import get_db_session
from app.schemas.performance import (
    BackendPerformanceProfile,
    PerformanceCapability,
    OptimizationRecommendation,
    PerformanceSimulationRequest,
    PerformanceSimulationResponse,
    GPUResourceProfile
)
from app.services.performance.advisory_scheduler import AdvisoryScheduler
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin/performance", tags=["performance-v2"])

# Mock backend data for simulation and capabilities
MOCK_BACKENDS = [
    BackendPerformanceProfile(
        backend_id="vllm-primary",
        backend_type="vllm",
        active_models=["llama-3-70b"],
        max_batch_size=128,
        throughput_tokens_sec=85.5,
        latency_ms_p50=120.0,
        gpu_resources=[
            GPUResourceProfile(
                gpu_id="0",
                total_vram_gb=80.0,
                used_vram_gb=45.0,
                utilization_percent=60.0,
                capabilities=[
                    PerformanceCapability.PAGED_ATTENTION,
                    PerformanceCapability.CONTINUOUS_BATCHING,
                    PerformanceCapability.TENSOR_PARALLEL
                ]
            )
        ]
    ),
    BackendPerformanceProfile(
        backend_id="llama-cpp-edge",
        backend_type="llama_cpp",
        active_models=["mistral-7b"],
        max_batch_size=8,
        throughput_tokens_sec=12.0,
        latency_ms_p50=450.0,
        gpu_resources=[
            GPUResourceProfile(
                gpu_id="0",
                total_vram_gb=8.0,
                used_vram_gb=7.5,
                utilization_percent=95.0,
                capabilities=[
                    PerformanceCapability.LAYER_OFFLOADING,
                    PerformanceCapability.FRACTIONAL_GPU
                ]
            )
        ]
    )
]

@router.get("/capabilities")
async def get_performance_capabilities():
    return [c.value for c in PerformanceCapability]

@router.get("/backends", response_model=List[BackendPerformanceProfile])
async def list_backend_performance():
    return MOCK_BACKENDS

@router.get("/recommendations", response_model=List[OptimizationRecommendation])
async def get_performance_recommendations(
    db: AsyncSession = Depends(get_db_session)
):
    scheduler = AdvisoryScheduler(db)
    return await scheduler.generate_recommendations(MOCK_BACKENDS)

@router.post("/simulate", response_model=PerformanceSimulationResponse)
async def simulate_performance(
    payload: PerformanceSimulationRequest,
    db: AsyncSession = Depends(get_db_session)
):
    scheduler = AdvisoryScheduler(db)
    return await scheduler.simulate_load(payload, MOCK_BACKENDS)
