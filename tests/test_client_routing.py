import pytest
from fastapi import HTTPException
from starlette.responses import JSONResponse

from app.api.client import _chat_with_fallback
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.services.inference_proxy import ForwardResult


class FakeProxy:
    def __init__(self):
        self.calls = []

    async def chat(
        self,
        payload,
        stream,
        include_reasoning,
        backend,
        backend_url,
        backend_name,
        backend_id=None,
        prompt_template=None,
        manage_slot=True,
    ):
        self.calls.append(backend_name)
        if backend_name == "primary":
            raise HTTPException(status_code=503, detail="data plane unavailable")
        return ForwardResult(
            response=JSONResponse({"ok": True, "backend": backend_name}),
            backend_name=backend_name,
            attempts=1,
            fallback_used=False,
            backend_errors=[],
        )


@pytest.mark.asyncio
async def test_chat_with_fallback_moves_to_next_backend_without_losing_error_context():
    model = ModelRegistry(model_id="gemma", provider="llama.cpp", model_file="gemma.gguf", context_length=2048, is_active=True, is_default=True, status="configured")
    primary = InferenceBackend(name="primary", provider="llama.cpp", backend_url="http://primary", is_active=True, status="healthy")
    secondary = InferenceBackend(name="secondary", provider="llama.cpp", backend_url="http://secondary", is_active=True, status="healthy")
    model.backend_routes = [
        ModelBackendRoute(priority=1, weight=100, state="healthy", inference_backend=primary),
        ModelBackendRoute(priority=2, weight=50, state="healthy", inference_backend=secondary),
    ]
    proxy = FakeProxy()

    result = await _chat_with_fallback(proxy, model, {"model": "gemma"}, False, False)

    assert proxy.calls == ["primary", "secondary"]
    assert result.backend_name == "secondary"
    assert result.attempts == 2
    assert result.fallback_used is True
    assert result.backend_errors[0]["backend_name"] == "primary"
    assert result.backend_errors[0]["status_code"] == 503
    assert result.response.body == b'{"ok":true,"backend":"secondary"}'
