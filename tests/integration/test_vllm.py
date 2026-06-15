import uuid
from unittest.mock import MagicMock, patch

import httpx
import pytest
from app.core.config import get_settings
from app.models.billing.billing_plan import BillingPlan
from app.models.core.api_key import ApiKey
from app.models.core.client import Client
from app.models.core.model_registry import ModelRegistry
from app.services.backend_registry import ensure_default_backends
from app.services.inference.backends.vllm_backend import VllmBackendService
from app.services.inference.backends.vllm_health import check_vllm_health
from app.services.model_registry import ensure_default_model
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_vllm_disabled_nao_aparece_como_backend_ativo(session, monkeypatch):
    monkeypatch.setenv("VLLM_BACKEND_ENABLED", "false")
    get_settings.cache_clear()
    settings = get_settings()

    # Re-run ensure_default_backends
    backends = await ensure_default_backends(session)
    vllm_backend = backends.get("vllm-local")
    assert vllm_backend is not None
    assert vllm_backend.is_active is False
    assert vllm_backend.status == "optional-disabled"


@pytest.mark.asyncio
async def test_vllm_healthcheck_mock_passa(monkeypatch):
    monkeypatch.setenv("VLLM_BACKEND_ENABLED", "true")
    get_settings.cache_clear()

    mock_resp = MagicMock(status_code=200)
    # Mock httpx AsyncClient request method
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await check_vllm_health()
        assert res["ok"] is True
        assert res["status"] == "healthy"


@pytest.mark.asyncio
async def test_vllm_timeout_tratado(monkeypatch):
    monkeypatch.setenv("VLLM_BACKEND_ENABLED", "true")
    get_settings.cache_clear()

    # Mock AsyncClient post to raise TimeoutException
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout occurred")):
        service = VllmBackendService()
        with pytest.raises(HTTPException) as exc:
            await service.chat_completions({"messages": [{"role": "user", "content": "hi"}]})
        assert exc.value.status_code == 504
        assert "timed out" in exc.value.detail


@pytest.mark.asyncio
async def test_vllm_chat_request_mapeado(monkeypatch):
    monkeypatch.setenv("VLLM_BACKEND_ENABLED", "true")
    monkeypatch.setenv("VLLM_DEFAULT_MODEL", "facebook/opt-125m")
    get_settings.cache_clear()

    mock_resp = MagicMock(status_code=200)
    mock_resp.json = MagicMock(
        return_value={"choices": [{"message": {"role": "assistant", "content": "Hello world"}}]}
    )

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        service = VllmBackendService()
        res = await service.chat_completions(
            {"messages": [{"role": "user", "content": "hi"}], "model": "default"}
        )
        assert res["choices"][0]["message"]["content"] == "Hello world"

        # Verify model was mapped to default configuration
        posted_payload = mock_post.call_args[1]["json"]
        assert posted_payload["model"] == "facebook/opt-125m"


@pytest.mark.asyncio
async def test_vllm_token_usage_registrado(admin_client, admin_token_headers, monkeypatch, session):
    # Setup vllm enabled and configured to route requests
    monkeypatch.setenv("VLLM_BACKEND_ENABLED", "true")
    monkeypatch.setenv("VLLM_BASE_URL", "http://127.0.0.1:9090/v1")
    get_settings.cache_clear()

    # 1. Create a client and API key
    plan = BillingPlan(
        id=uuid.uuid4(),
        code="basic-vllm",
        name="Basic Plan vLLM",
        rate_limit_per_minute=100,
        daily_token_quota=100000,
        weekly_token_quota=500000,
        monthly_token_quota=1000000,
        max_output_tokens=1024,
    )
    session.add(plan)
    await session.commit()

    client = Client(
        id=uuid.uuid4(),
        name="vllm-test-client",
        billing_status="active",
        billing_plan_id=plan.id,
    )
    session.add(client)
    await session.commit()

    api_key = ApiKey(
        client_id=client.id,
        name="vllm-key",
        key_prefix="sk-vllm",
        key_hash="hash-vllm",
        is_active=True,
    )
    session.add(api_key)
    await session.commit()

    # Enable slot management
    with patch("app.services.queue_manager.QueueManager.slot") as mock_slot:
        mock_slot.return_value.__aenter__.return_value = None

        # Re-ensure default backends and model mapping
        backends = await ensure_default_backends(session)
        assert "vllm-local" in backends
        vllm_backend = backends["vllm-local"]
        vllm_backend.is_active = True
        session.add(vllm_backend)
        await session.commit()

        await ensure_default_model(session)
        await session.commit()
        from sqlalchemy import select

        vllm_model_res = await session.execute(
            select(ModelRegistry).where(ModelRegistry.model_alias == "vllm-default")
        )
        vllm_model = vllm_model_res.scalar_one()

        # Mock the real call payload to return typical openai structure
        mock_resp = MagicMock(status_code=200)
        mock_resp.json = MagicMock(
            return_value={
                "choices": [{"message": {"role": "assistant", "content": "mock text output"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
            }
        )

        with patch("httpx.AsyncClient.post", return_value=mock_resp):
            resp = await admin_client.post(
                "/v1/chat/completions",
                json={
                    "model": vllm_model.model_id,
                    "messages": [{"role": "user", "content": "hi"}],
                },
                headers={"Authorization": "Bearer sk-vllm.val"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "usage" in data
            assert data["usage"]["prompt_tokens"] > 0
            assert data["usage"]["completion_tokens"] > 0


@pytest.mark.asyncio
async def test_vllm_fallback_para_outro_backend_funciona(
    admin_client, admin_token_headers, monkeypatch, session
):
    monkeypatch.setenv("VLLM_BACKEND_ENABLED", "true")
    monkeypatch.setenv("VLLM_BASE_URL", "http://127.0.0.1:9090/v1")  # Definitely offline
    get_settings.cache_clear()

    # Set up client and API key
    plan = BillingPlan(
        id=uuid.uuid4(),
        code="fallback-plan",
        name="Fallback Plan",
        rate_limit_per_minute=100,
        daily_token_quota=100000,
        weekly_token_quota=500000,
        monthly_token_quota=1000000,
        max_output_tokens=1024,
    )
    session.add(plan)
    await session.commit()

    client = Client(
        id=uuid.uuid4(),
        name="fallback-client",
        billing_status="active",
        billing_plan_id=plan.id,
    )
    session.add(client)
    await session.commit()

    api_key = ApiKey(
        client_id=client.id,
        name="fallback-key",
        key_prefix="sk-fallback",
        key_hash="hash-fallback",
        is_active=True,
    )
    session.add(api_key)
    await session.commit()

    # Re-run ensure default backends & default model
    backends = await ensure_default_backends(session)
    vllm_backend = backends["vllm-local"]
    vllm_backend.is_active = True
    session.add(vllm_backend)
    await session.commit()

    await ensure_default_model(session)
    await session.commit()
    from sqlalchemy import select

    vllm_model_res = await session.execute(
        select(ModelRegistry).where(ModelRegistry.model_alias == "vllm-default")
    )
    vllm_model = vllm_model_res.scalar_one()

    # Add fallback route to gemma-local backend (which we mock to respond successfully)
    from app.models.core.model_backend_route import ModelBackendRoute

    fallback_route = ModelBackendRoute(
        model_registry_id=vllm_model.id,
        inference_backend_id=backends["gemma-local"].id,
        priority=2,
        weight=100,
        state="healthy",
    )
    session.add(fallback_route)
    await session.commit()

    with patch("app.services.queue_manager.QueueManager.slot") as mock_slot:
        mock_slot.return_value.__aenter__.return_value = None

        # When client.post vllm URL fails, it falls back to gemma-local, which succeeds
        async def side_effect(endpoint, **kwargs):
            if "9090" in str(mock_post.call_args[0][0]):
                # vLLM fails
                raise httpx.ConnectError("Connection refused")
            # Fallback gemma-local succeeds
            mock_success = MagicMock(status_code=200)
            mock_success.json = MagicMock(
                return_value={
                    "choices": [
                        {"message": {"role": "assistant", "content": "hello from fallback"}}
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
                }
            )
            return mock_success

        with patch("httpx.AsyncClient.post", side_effect=side_effect) as mock_post:
            resp = await admin_client.post(
                "/v1/chat/completions",
                json={
                    "model": vllm_model.model_id,
                    "messages": [{"role": "user", "content": "hi"}],
                },
                headers={"Authorization": "Bearer sk-fallback.val"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["choices"][0]["message"]["content"] == "hello from fallback"
