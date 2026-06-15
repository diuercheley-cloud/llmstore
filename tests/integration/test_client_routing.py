import pytest
from app.api.client import _chat_with_fallback
from app.models.core.inference_backend import InferenceBackend
from app.models.core.model_backend_route import ModelBackendRoute
from app.models.core.model_registry import ModelRegistry
from app.services.inference_proxy import ForwardResult
from fastapi import HTTPException
from starlette.responses import JSONResponse


class FakeProxy:
    def __init__(self):
        self.calls = []
        self.last_kwargs = None

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
        **kwargs,
    ):
        self.calls.append(backend_name)
        self.last_kwargs = kwargs
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
    model = ModelRegistry(
        model_id="gemma",
        provider="llama.cpp",
        model_file="gemma.gguf",
        context_length=2048,
        is_active=True,
        is_default=True,
        status="configured",
    )
    primary = InferenceBackend(
        name="primary",
        provider="llama.cpp",
        backend_url="http://primary",
        is_active=True,
        status="healthy",
    )
    secondary = InferenceBackend(
        name="secondary",
        provider="llama.cpp",
        backend_url="http://secondary",
        is_active=True,
        status="healthy",
    )
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


@pytest.mark.asyncio
async def test_chat_with_fallback_propagates_backend_auth_and_plan_context():
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.services.billing.core import EffectivePlan

    model = ModelRegistry(
        model_id="gemma",
        provider="llama.cpp",
        model_file="gemma.gguf",
        context_length=2048,
        is_active=True,
        is_default=True,
        status="configured",
    )
    backend = InferenceBackend(
        name="propagation",
        provider="llama.cpp",
        backend_url="http://primary",
        is_active=True,
        status="healthy",
        metadata_json='{"api_key":"backend-secret"}',
    )
    model.prompt_template = "tmpl"
    model.backend_routes = [
        ModelBackendRoute(priority=1, weight=100, state="healthy", inference_backend=backend),
    ]

    client = MagicMock()
    client.metadata_json = '{"is_admin": true}'
    client.billing_plan.routing_policy_json = None

    effective_plan = EffectivePlan(
        code="pro",
        name="Pro",
        rate_limit_per_minute=10,
        daily_token_quota=1000,
        weekly_token_quota=5000,
        monthly_token_quota=10000,
        max_output_tokens=512,
        allow_streaming=True,
    )

    proxy = FakeProxy()

    with patch(
        "app.api.client.resolve_effective_plan_for_session", new_callable=AsyncMock
    ) as mock_resolve:
        mock_resolve.return_value = effective_plan
        result = await _chat_with_fallback(
            proxy, model, {"model": "gemma"}, False, True, client=client
        )

    assert result.backend_name == "propagation"
    assert proxy.last_kwargs["api_key"] == "backend-secret"
    assert proxy.last_kwargs["plan_code"] == "pro"
    assert proxy.last_kwargs["is_admin"] is True
