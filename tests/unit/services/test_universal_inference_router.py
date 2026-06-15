from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.models.core.inference_backend import InferenceBackend
from app.services.inference.backend_router import UniversalInferenceRouter


class FakeProxy:
    def __init__(self) -> None:
        self.health_backend = AsyncMock(
            return_value={"ok": True, "status": "healthy", "latency_ms": 12.5}
        )
        self.list_models = AsyncMock(return_value={"data": [{"id": "model-a"}, {"id": "model-b"}]})


@pytest.mark.asyncio
async def test_capabilities_for_common_local_backends():
    backend = InferenceBackend(
        name="ollama-local",
        provider="ollama",
        backend_url="http://localhost:11434",
    )
    router = UniversalInferenceRouter(FakeProxy())

    caps = router.capabilities_for(backend)

    assert caps.streaming is True
    assert caps.embeddings is True
    assert caps.tool_calling is False
    assert caps.vision is True
    assert caps.batching is False


@pytest.mark.asyncio
async def test_report_for_includes_benchmark_score():
    backend = InferenceBackend(
        name="vllm-main",
        provider="vllm",
        backend_url="http://localhost:8000",
    )
    proxy = FakeProxy()
    router = UniversalInferenceRouter(proxy)

    report = await router.report_for(backend)

    assert report.health["ok"] is True
    assert report.benchmark["model_count"] == 2
    assert report.benchmark["score"] > 0
    assert report.capabilities.batching is True
