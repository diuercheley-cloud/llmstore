import httpx
import pytest
from fastapi import HTTPException

from app.services.circuit_breaker import CircuitBreaker
from app.services.inference_proxy import InferenceProxy


class DummyQueueManager:
    def slot(self, backend_id=None):  # pragma: no cover
        raise AssertionError("slot management should not be used in this unit test")


@pytest.mark.asyncio
async def test_json_forward_400_does_not_open_circuit_breaker():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad request"})

    proxy = InferenceProxy(DummyQueueManager(), CircuitBreaker())
    proxy.circuit_breaker.failure_threshold = 1

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://backend")
    try:
        proxy._client_for_backend = lambda backend, backend_url: client
        with pytest.raises(HTTPException) as exc:
            await proxy._json_forward("/v1/chat/completions", {"model": "gemma", "messages": [{"role": "user", "content": "x"}]}, backend="llama.cpp", backend_url="http://backend", backend_name="gemma-local")

        assert exc.value.status_code == 400
        assert proxy.circuit_breaker.failures == 0
        assert proxy.circuit_breaker.opened_at == 0.0
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_stream_forward_400_does_not_open_circuit_breaker(monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad request"})

    proxy = InferenceProxy(DummyQueueManager(), CircuitBreaker())
    proxy.circuit_breaker.failure_threshold = 1
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://backend")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: client)

    try:
        with pytest.raises(HTTPException) as exc:
            await proxy._streaming_forward(
                "/v1/chat/completions",
                {"model": "gemma", "messages": [{"role": "user", "content": "x"}]},
                backend="llama.cpp",
                backend_url="http://backend",
                backend_name="gemma-local",
            )

        assert exc.value.status_code == 400
        assert proxy.circuit_breaker.failures == 0
        assert proxy.circuit_breaker.opened_at == 0.0
    finally:
        await client.aclose()


def test_prepare_chat_payload_uses_qwen_template_and_disables_reasoning():
    proxy = InferenceProxy(DummyQueueManager(), CircuitBreaker())

    prepared = proxy._prepare_chat_payload(
        {"model": "gemma", "messages": [{"role": "user", "content": "oi"}]},
        include_reasoning=False,
        backend="llama.cpp",
        prompt_template="qwen",
    )

    assert "chat_template" in prepared
    assert "<|im_end|>" in prepared["chat_template"]
    assert prepared["reasoning_format"] == "none"
    assert prepared["chat_template_kwargs"]["enable_thinking"] is False


def test_prepare_chat_payload_uses_gemma_template_and_disables_reasoning():
    proxy = InferenceProxy(DummyQueueManager(), CircuitBreaker())

    prepared = proxy._prepare_chat_payload(
        {"model": "gemma", "messages": [{"role": "user", "content": "oi"}]},
        include_reasoning=False,
        backend="llama.cpp",
        prompt_template="gemma",
    )

    assert prepared["repeat_penalty"] == 1.2
    assert prepared["reasoning_format"] == "none"
    assert prepared["chat_template_kwargs"]["enable_thinking"] is False
