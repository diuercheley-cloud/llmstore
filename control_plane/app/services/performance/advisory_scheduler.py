import logging
import uuid

from app.schemas.performance import (
    BackendPerformanceProfile,
    OptimizationRecommendation,
    PerformanceCapability,
    PerformanceSimulationRequest,
    PerformanceSimulationResponse,
    SchedulingDecision,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AdvisoryScheduler:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_scheduling_recommendation(
        self, model_id: str, backends: list[BackendPerformanceProfile]
    ) -> SchedulingDecision:
        """
        Advisory scheduling logic that recommends a backend based on available VRAM and capabilities.
        """
        if not backends:
            return SchedulingDecision(
                selected_backend_id="cpu-fallback",
                reasoning="No GPU backends available. Falling back to CPU.",
                estimated_latency_ms=5000.0,
            )

        # Sort backends by available VRAM
        sorted_backends = sorted(
            backends,
            key=lambda b: sum(gpu.total_vram_gb - gpu.used_vram_gb for gpu in b.gpu_resources),
            reverse=True,
        )

        best_backend = sorted_backends[0]
        vram_available = sum(
            gpu.total_vram_gb - gpu.used_vram_gb for gpu in best_backend.gpu_resources
        )

        reasoning = f"Selected backend {best_backend.backend_id} based on available VRAM ({vram_available:.1f} GB)."

        if vram_available < 4.0:
            reasoning += " Warning: Low VRAM detected, performance may be degraded."

        return SchedulingDecision(
            selected_backend_id=best_backend.backend_id,
            reasoning=reasoning,
            estimated_latency_ms=best_backend.latency_ms_p50,
        )

    async def generate_recommendations(
        self, backends: list[BackendPerformanceProfile]
    ) -> list[OptimizationRecommendation]:
        """
        Analyzes backends and generates optimization recommendations.
        """
        recommendations = []

        for b in backends:
            vram_available = sum(gpu.total_vram_gb - gpu.used_vram_gb for gpu in b.gpu_resources)

            # 1. Quantization Recommendation
            if vram_available < 8.0 and b.backend_type != "cpu":
                recommendations.append(
                    OptimizationRecommendation(
                        id=str(uuid.uuid4()),
                        title="Enable 4-bit Quantization",
                        description=f"Backend {b.backend_id} has low VRAM ({vram_available:.1f} GB). Enabling 4-bit quantization (AWQ/GPTQ) will reduce memory usage by ~70%.",
                        impact="high",
                        priority="high",
                        target_backend_id=b.backend_id,
                        suggested_config={"quantization": "4bit", "format": "awq"},
                    )
                )

            # 2. vLLM specific recommendations
            if b.backend_type == "vllm":
                if PerformanceCapability.CONTINUOUS_BATCHING not in b.gpu_resources[0].capabilities:
                    recommendations.append(
                        OptimizationRecommendation(
                            id=str(uuid.uuid4()),
                            title="Enable Continuous Batching",
                            description=f"vLLM backend {b.backend_id} can benefit from continuous batching to increase throughput by 2x-4x.",
                            impact="high",
                            priority="medium",
                            target_backend_id=b.backend_id,
                            suggested_config={"enable_continuous_batching": True},
                        )
                    )

                if PerformanceCapability.PAGED_ATTENTION not in b.gpu_resources[0].capabilities:
                    recommendations.append(
                        OptimizationRecommendation(
                            id=str(uuid.uuid4()),
                            title="Optimize KV Cache with PagedAttention",
                            description="PagedAttention reduces memory fragmentation and allows for larger batch sizes.",
                            impact="medium",
                            priority="medium",
                            target_backend_id=b.backend_id,
                            suggested_config={"use_paged_attention": True},
                        )
                    )

            # 3. Speculative Decoding Recommendation
            if b.throughput_tokens_sec < 10.0 and b.backend_type != "cpu":
                recommendations.append(
                    OptimizationRecommendation(
                        id=str(uuid.uuid4()),
                        title="Configure Speculative Decoding",
                        description="Low throughput detected. Using a smaller draft model can speed up generation by up to 2x.",
                        impact="high",
                        priority="low",
                        target_backend_id=b.backend_id,
                        suggested_config={
                            "speculative_decoding": {"draft_model": "tiny-llama-1.1b"}
                        },
                    )
                )

        return recommendations

    async def simulate_load(
        self, req: PerformanceSimulationRequest, backends: list[BackendPerformanceProfile]
    ) -> PerformanceSimulationResponse:
        """
        Simulates load and predicts performance bottlenecks.
        """
        # Basic heuristic simulation
        total_tokens = (req.avg_prompt_tokens + req.avg_completion_tokens) * req.concurrent_requests

        # Assume we use the first available GPU backend
        gpu_backends = [b for b in backends if b.backend_type != "cpu"]
        target = gpu_backends[0] if gpu_backends else backends[0]

        throughput = target.throughput_tokens_sec
        latency = (total_tokens / throughput) * 1000 / req.concurrent_requests

        bottlenecks = []
        if req.concurrent_requests > target.max_batch_size:
            bottlenecks.append("Max batch size exceeded. Requests will be queued.")

        vram_per_request = 0.5  # GB heuristic
        if (req.concurrent_requests * vram_per_request) > sum(
            gpu.total_vram_gb for gpu in target.gpu_resources
        ):
            bottlenecks.append("VRAM Pressure: High concurrency may lead to OOM or swapping.")

        recs = await self.generate_recommendations([target])

        return PerformanceSimulationResponse(
            overall_throughput=throughput,
            avg_latency_ms=latency,
            bottlenecks=bottlenecks,
            recommendations=recs,
        )
