import logging
from typing import Any, Dict, List, Optional, Tuple

from app.models.inference_backend import InferenceBackend
from app.services.inference.backends.base import Capability, InferenceBackendBase
from app.services.inference.backends.openai_compatible_backend import OpenAICompatibleBackend
from app.services.inference.backends.tgi_backend import TGIBackend
from app.services.inference.backends.vllm_backend import VLLMBackend
from app.services.inference.backends.llama_cpp_backend import LlamaCppBackend
from app.services.runtime.hardware_detection import detect_hardware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class InferenceRouter:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.hardware = detect_hardware()
        self.routing_log = []

    async def get_best_backend(
        self, 
        model_name: str, 
        capability: Capability, 
        tenant_id: Optional[str] = None
    ) -> Tuple[Optional[InferenceBackendBase], str]:
        """
        Selects the best backend for the given request.
        Returns (backend_adapter, reason).
        """
        # 1. Fetch active backends
        stmt = select(InferenceBackend).where(InferenceBackend.is_active == True)
        result = await self.session.execute(stmt)
        backends = result.scalars().all()

        if not backends:
            reason = "No active backends found"
            self._log_decision(model_name, capability, None, reason)
            return None, reason

        # 2. Filter by model and capability
        # In a real implementation, we would check which models are loaded in each backend
        # For now, let's assume we have a mapping or the backend can tell us
        
        candidates = []
        for b in backends:
            adapter = self._get_adapter(b)
            if not adapter:
                continue
                
            if adapter.supports_capability(capability):
                # Check if model is supported (simplified)
                # In a real system, we'd check ModelRegistry or call adapter.list_models()
                candidates.append((b, adapter))

        if not candidates:
            reason = f"No backend supports capability {capability}"
            self._log_decision(model_name, capability, None, reason)
            return None, reason

        # 3. Simple selection logic (prioritize vLLM if available, then TGI, then others)
        # This can be expanded with latency, cost, etc.
        candidates.sort(key=lambda x: self._get_priority(x[0].provider), reverse=True)
        
        selected_backend, selected_adapter = candidates[0]
        reason = f"Selected {selected_backend.name} ({selected_backend.provider}) based on priority"
        
        self._log_decision(model_name, capability, selected_backend.name, reason)
        return selected_adapter, reason

    def _get_adapter(self, backend: InferenceBackend) -> Optional[InferenceBackendBase]:
        try:
            if backend.provider == "vllm":
                return VLLMBackend(backend.name, backend.backend_url)
            elif backend.provider == "tgi":
                return TGIBackend(backend.name, backend.backend_url)
            elif backend.provider in {"openai_compatible", "openai", "anthropic", "deepseek", "openrouter", "lmstudio"}:
                return OpenAICompatibleBackend(backend.name, backend.backend_url)
            elif backend.provider == "ollama":
                return OpenAICompatibleBackend(backend.name, backend.backend_url)
            elif backend.provider == "llama.cpp":
                return LlamaCppBackend(backend.name, backend.backend_url)
            return None
        except Exception as e:
            logger.error(f"Failed to create adapter for {backend.name}: {e}")
            return None

    def _get_priority(self, provider: str) -> int:
        priorities = {
            "vllm": 100,
            "tgi": 90,
            "lmstudio": 70,
            "ollama": 60,
            "openai_compatible": 50,
            "openai": 50,
            "anthropic": 50,
            "deepseek": 50,
            "openrouter": 50,
            "llama.cpp": 10,
        }
        return priorities.get(provider, 0)

    def _log_decision(self, model: str, capability: Capability, backend_name: Optional[str], reason: str):
        decision = {
            "model": model,
            "capability": capability,
            "selected_backend": backend_name,
            "reason": reason,
            "hardware": {
                "gpus": self.hardware.gpu_count,
                "vram": self.hardware.vram_total_gb
            }
        }
        self.routing_log.append(decision)
        logger.info(f"Routing decision: {decision}")

    def get_last_decision(self) -> Optional[Dict[str, Any]]:
        return self.routing_log[-1] if self.routing_log else None
