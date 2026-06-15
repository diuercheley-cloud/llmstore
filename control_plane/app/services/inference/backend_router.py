from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from app.models.core.inference_backend import InferenceBackend
from app.services.inference.backends.universal import BackendCapabilities
from app.services.inference_proxy import InferenceProxy
from app.services.model_policy import model_supports_native_tools
from fastapi import HTTPException


@dataclass(slots=True)
class BackendCapabilityReport:
    backend_id: str
    name: str
    provider: str
    capabilities: BackendCapabilities
    health: dict[str, Any]
    benchmark: dict[str, Any]

    def model_dump(self) -> dict[str, Any]:
        return {
            "backend_id": self.backend_id,
            "name": self.name,
            "provider": self.provider,
            "capabilities": self.capabilities.model_dump(),
            "health": self.health,
            "benchmark": self.benchmark,
        }


class UniversalInferenceRouter:
    def __init__(self, proxy: InferenceProxy):
        self.proxy = proxy

    def capabilities_for(self, backend: InferenceBackend) -> BackendCapabilities:
        provider = (backend.provider or "").lower()
        metadata = backend.metadata_json or ""
        supports_tools = provider in {
            "vllm",
            "tgi",
            "tensorrt-llm",
            "mlx",
        } or model_supports_native_tools(provider, metadata)
        supports_streaming = provider in {
            "ollama",
            "llama.cpp",
            "vllm",
            "tgi",
            "tensorrt-llm",
            "mlx",
            "openai_compatible",
        }
        supports_embeddings = provider in {
            "ollama",
            "llama.cpp",
            "vllm",
            "tgi",
            "mlx",
            "openai_compatible",
        }
        supports_vision = provider in {"ollama", "vllm", "mlx", "tgi", "tensorrt-llm"}
        supports_batching = provider in {"vllm", "tgi", "tensorrt-llm"}
        notes = []
        if provider == "llama.cpp":
            notes.append("OpenAI-compatible in server mode")
        if provider == "mlx":
            notes.append("Optimized for Apple Silicon")
        if provider == "tensorrt-llm":
            notes.append("GPU acceleration oriented")
        return BackendCapabilities(
            streaming=supports_streaming,
            embeddings=supports_embeddings,
            tool_calling=supports_tools,
            vision=supports_vision,
            batching=supports_batching,
            notes=notes,
        )

    async def report_for(self, backend: InferenceBackend) -> BackendCapabilityReport:
        started = perf_counter()
        health = await self.proxy.health_backend(backend)
        model_error: dict[str, Any] | None = None
        try:
            models = await self.proxy.list_models(base_url=backend.backend_url)
        except HTTPException as exc:
            models = {"data": []}
            model_error = {
                "status_code": exc.status_code,
                "detail": exc.detail,
            }
        except Exception as exc:
            models = {"data": []}
            model_error = {
                "status_code": None,
                "detail": str(exc),
            }
        benchmark = {
            "latency_ms": round((perf_counter() - started) * 1000, 2),
            "model_count": len(models.get("data", []))
            if isinstance(models, dict)
            else len(models or []),
            "score": self._score_backend(backend, health, models),
        }
        if model_error is not None:
            benchmark["model_listing_error"] = model_error
        return BackendCapabilityReport(
            backend_id=str(backend.id),
            name=backend.name,
            provider=backend.provider,
            capabilities=self.capabilities_for(backend),
            health=health,
            benchmark=benchmark,
        )

    def _score_backend(
        self, backend: InferenceBackend, health: dict[str, Any], models: Any
    ) -> float:
        score = 0.0
        if health.get("ok") is True or health.get("status") in {"healthy", "degraded"}:
            score += 50.0
        caps = self.capabilities_for(backend)
        score += sum(
            value
            for value in (
                10.0 if caps.streaming else 0.0,
                10.0 if caps.embeddings else 0.0,
                10.0 if caps.tool_calling else 0.0,
                5.0 if caps.vision else 0.0,
                5.0 if caps.batching else 0.0,
            )
        )
        model_count = len(models.get("data", [])) if isinstance(models, dict) else len(models or [])
        score += min(model_count, 5) * 2.0
        latency = float(health.get("latency_ms") or 0.0)
        score -= min(latency / 100.0, 10.0)
        if backend.provider in {"ollama", "llama.cpp", "mlx"}:
            score += 5.0
        return round(score, 2)
