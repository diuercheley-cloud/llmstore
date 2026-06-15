import logging
from datetime import timedelta
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.core.inference_backend import InferenceBackend
from app.models.core.inference_routing_decision import InferenceRoutingDecision
from app.services.inference.backends.base import Capability, InferenceBackendBase
from app.services.inference.backends.llama_cpp_backend import LlamaCppBackend
from app.services.inference.backends.openai_compatible_backend import OpenAICompatibleBackend
from app.services.inference.backends.tgi_backend import TGIBackend
from app.services.inference.backends.vllm_backend import VLLMBackend
from app.services.runtime.hardware_detection import detect_hardware
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

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
        tenant_id: str | None = None,
        request_id: str | None = None,
        client_id: str | None = None,
        routing_policy_version: int | None = None,
        latency_ms: int | None = None,
        success: bool = True,
        error_code: str | None = None,
    ) -> tuple[InferenceBackendBase | None, str]:
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

            # Persist failure decision
            decision_record = InferenceRoutingDecision(
                request_id=request_id,
                tenant_id=tenant_id,
                client_id=client_id,
                selected_backend=None,
                selected_model=model_name,
                candidate_backends={"backends": []},
                routing_policy_version=routing_policy_version,
                reason=reason,
                latency_ms=latency_ms,
                success=False,
                error_code=error_code or "NO_ACTIVE_BACKENDS",
            )
            self.session.add(decision_record)
            await self.session.flush()

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
                # In a system like this, we'd check ModelRegistry or call adapter.list_models()
                candidates.append((b, adapter))

        if not candidates:
            reason = f"No backend supports capability {capability}"
            self._log_decision(model_name, capability, None, reason)

            # Persist failure decision
            decision_record = InferenceRoutingDecision(
                request_id=request_id,
                tenant_id=tenant_id,
                client_id=client_id,
                selected_backend=None,
                selected_model=model_name,
                candidate_backends={"backends": []},
                routing_policy_version=routing_policy_version,
                reason=reason,
                latency_ms=latency_ms,
                success=False,
                error_code=error_code or "UNSUPPORTED_CAPABILITY",
            )
            self.session.add(decision_record)
            await self.session.flush()

            return None, reason

        # 3. Simple selection logic (prioritize vLLM if available, then TGI, then others)
        # This can be expanded with latency, cost, etc.
        candidates.sort(key=lambda x: self._get_priority(x[0].provider), reverse=True)

        selected_backend, selected_adapter = candidates[0]
        reason = f"Selected {selected_backend.name} ({selected_backend.provider}) based on priority"

        self._log_decision(model_name, capability, selected_backend.name, reason)

        # Persist success/custom decision
        decision_record = InferenceRoutingDecision(
            request_id=request_id,
            tenant_id=tenant_id,
            client_id=client_id,
            selected_backend=selected_backend.name,
            selected_model=model_name,
            candidate_backends={"backends": [b.name for b, _ in candidates]},
            routing_policy_version=routing_policy_version,
            reason=reason,
            latency_ms=latency_ms,
            success=success,
            error_code=error_code,
        )
        self.session.add(decision_record)
        await self.session.flush()

        return selected_adapter, reason

    def _get_adapter(self, backend: InferenceBackend) -> InferenceBackendBase | None:
        try:
            if backend.provider == "vllm":
                return VLLMBackend(backend.name, backend.backend_url)
            elif backend.provider == "tgi":
                return TGIBackend(backend.name, backend.backend_url)
            elif (
                backend.provider
                in {
                    "openai_compatible",
                    "openai",
                    "anthropic",
                    "deepseek",
                    "openrouter",
                    "lmstudio",
                }
                or backend.provider == "ollama"
            ):
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

    def _log_decision(
        self, model: str, capability: Capability, backend_name: str | None, reason: str
    ):
        decision = {
            "model": model,
            "capability": capability,
            "selected_backend": backend_name,
            "reason": reason,
            "hardware": {"gpus": self.hardware.gpu_count, "vram": self.hardware.vram_total_gb},
        }
        self.routing_log.append(decision)
        logger.info(f"Routing decision: {decision}")

    def get_last_decision(self) -> dict[str, Any] | None:
        return self.routing_log[-1] if self.routing_log else None

    async def cleanup_old_decisions(self, retention_days: int | None = None) -> int:
        """
        Deletes decisions older than the configured retention days.
        Returns the number of deleted records.
        """
        cfg = get_settings()
        days = (
            retention_days
            if retention_days is not None
            else getattr(cfg, "commercial_routing_decision_retention_days", 30)
        )

        cutoff = utc_now() - timedelta(days=days)
        stmt = delete(InferenceRoutingDecision).where(InferenceRoutingDecision.created_at < cutoff)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0
