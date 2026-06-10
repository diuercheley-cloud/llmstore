import pytest
import uuid
from app.schemas.performance import (
    BackendPerformanceProfile,
    PerformanceCapability,
    GPUResourceProfile,
    PerformanceSimulationRequest
)
from app.services.performance.advisory_scheduler import AdvisoryScheduler

@pytest.fixture
def mock_backends():
    return [
        BackendPerformanceProfile(
            backend_id="vllm-high-vram",
            backend_type="vllm",
            active_models=["llama-3"],
            max_batch_size=128,
            throughput_tokens_sec=50.0,
            latency_ms_p50=100.0,
            gpu_resources=[
                GPUResourceProfile(
                    gpu_id="0",
                    total_vram_gb=80.0,
                    used_vram_gb=10.0,
                    utilization_percent=10.0,
                    capabilities=[PerformanceCapability.CONTINUOUS_BATCHING]
                )
            ]
        ),
        BackendPerformanceProfile(
            backend_id="llama-cpp-low-vram",
            backend_type="llama_cpp",
            active_models=["mistral"],
            max_batch_size=4,
            throughput_tokens_sec=5.0,
            latency_ms_p50=500.0,
            gpu_resources=[
                GPUResourceProfile(
                    gpu_id="0",
                    total_vram_gb=8.0,
                    used_vram_gb=7.5,
                    utilization_percent=90.0,
                    capabilities=[]
                )
            ]
        )
    ]

@pytest.mark.asyncio
async def test_scheduler_deterministic_selection(session, mock_backends):
    scheduler = AdvisoryScheduler(session)
    decision = await scheduler.get_scheduling_recommendation("llama-3", mock_backends)
    
    assert decision.selected_backend_id == "vllm-high-vram"
    assert "80.0 GB" in decision.reasoning or "70.0 GB" in decision.reasoning

@pytest.mark.asyncio
async def test_quantization_recommendation_on_low_vram(session, mock_backends):
    scheduler = AdvisoryScheduler(session)
    # Filter only the low vram backend
    recs = await scheduler.generate_recommendations([mock_backends[1]])
    
    assert any("Quantization" in r.title for r in recs)
    assert recs[0].priority == "high"

@pytest.mark.asyncio
async def test_vllm_optimization_recommendations(session, mock_backends):
    scheduler = AdvisoryScheduler(session)
    recs = await scheduler.generate_recommendations([mock_backends[0]])
    
    # mock_backends[0] (vLLM) has CONTINUOUS_BATCHING but lacks PAGED_ATTENTION
    assert any("PagedAttention" in r.title for r in recs)
    assert not any("Continuous Batching" in r.title for r in recs)

@pytest.mark.asyncio
async def test_cpu_fallback_recommendation(session):
    scheduler = AdvisoryScheduler(session)
    decision = await scheduler.get_scheduling_recommendation("llama-3", [])
    
    assert decision.selected_backend_id == "cpu-fallback"
    assert "No GPU" in decision.reasoning

@pytest.mark.asyncio
async def test_load_simulation_bottlenecks(session, mock_backends):
    scheduler = AdvisoryScheduler(session)
    req = PerformanceSimulationRequest(
        models=["llama-3"],
        concurrent_requests=200, # higher than max_batch_size (128)
        avg_prompt_tokens=100,
        avg_completion_tokens=100
    )
    
    res = await scheduler.simulate_load(req, mock_backends)
    assert res.overall_throughput > 0
    assert any("Max batch size exceeded" in b for b in res.bottlenecks)
