from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PerformanceCapability(str, Enum):
    SPECULATIVE_DECODING = "speculative_decoding"
    PAGED_ATTENTION = "paged_attention"
    CONTINUOUS_BATCHING = "continuous_batching"
    TENSOR_PARALLEL = "tensor_parallel"
    PIPELINE_PARALLEL = "pipeline_parallel"
    KV_CACHE_REUSE = "kv_cache_reuse"
    LAYER_OFFLOADING = "layer_offloading"
    MIG = "mig"
    FRACTIONAL_GPU = "fractional_gpu"
    TIME_SLICING = "time_slicing"


class GPUResourceProfile(BaseModel):
    gpu_id: str
    total_vram_gb: float
    used_vram_gb: float
    utilization_percent: float
    capabilities: List[PerformanceCapability] = Field(default_factory=list)


class BackendPerformanceProfile(BaseModel):
    backend_id: str
    backend_type: str  # vllm, llama_cpp, tgi, etc.
    active_models: List[str]
    max_batch_size: int
    throughput_tokens_sec: float
    latency_ms_p50: float
    gpu_resources: List[GPUResourceProfile] = Field(default_factory=list)


class SchedulingDecision(BaseModel):
    selected_backend_id: str
    reasoning: str
    estimated_latency_ms: float
    queue_position: int = 0


class OptimizationRecommendation(BaseModel):
    id: str
    title: str
    description: str
    impact: str  # high, medium, low
    priority: str  # high, medium, low
    target_backend_id: str
    suggested_config: Dict[str, Any]
    action_required: bool = True


class PerformanceSimulationRequest(BaseModel):
    models: List[str]
    concurrent_requests: int
    avg_prompt_tokens: int
    avg_completion_tokens: int


class PerformanceSimulationResponse(BaseModel):
    overall_throughput: float
    avg_latency_ms: float
    bottlenecks: List[str]
    recommendations: List[OptimizationRecommendation]
