import json

import httpx
import pytest

from scripts.llm_harness.providers import ControlPlaneProvider


def _response(status_code: int, payload, request: httpx.Request) -> httpx.Response:
    if isinstance(payload, (dict, list)):
        return httpx.Response(status_code, json=payload, request=request)
    return httpx.Response(status_code, text=payload, request=request)


@pytest.mark.asyncio
async def test_control_plane_health_and_list_agents():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return _response(200, {"ok": True}, request)
        if request.url.path == "/v1/agents":
            return _response(200, [{"id": "agent-1"}], request)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    provider = ControlPlaneProvider(
        {
            "base_url": "http://control-plane",
            "agent_id": "agent-1",
            "transport": httpx.MockTransport(handler),
        }
    )

    health = await provider.health_check()
    agents = await provider.list_agents()

    assert health["status"] == "healthy"
    assert health["agents_count"] == 1
    assert agents == [{"id": "agent-1"}]


@pytest.mark.asyncio
async def test_control_plane_start_run_and_completed_event():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.url.path == "/v1/agents":
            return _response(200, [{"id": "agent-1"}], request)
        if request.url.path == "/v1/agents/agent-1/runs":
            return _response(200, {"id": "run-1"}, request)
        if request.url.path == "/v1/agents/runs/run-1/events":
            payload = (
                "event: tool.called\n"
                'data: {"tool_name":"run_shell","parameters":{"command":"pytest -q"}}\n\n'
                "event: run.completed\n"
                'data: {"message":"done"}\n\n'
            )
            return _response(200, payload, request)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    provider = ControlPlaneProvider(
        {
            "base_url": "http://control-plane",
            "agent_id": "agent-1",
            "transport": httpx.MockTransport(handler),
        }
    )

    run_data = await provider.start_run("Fix it")
    response = await provider.chat_completion([{"role": "user", "content": "Fix it"}])

    assert run_data["id"] == "run-1"
    content = json.loads(response["choices"][0]["message"]["content"])
    assert content["action_type"] == "run_shell"
    assert content["command"] == "pytest -q"
    assert requests.count(("POST", "/v1/agents/agent-1/runs")) == 2


@pytest.mark.asyncio
async def test_control_plane_run_completed_with_output_action_and_secrets_redacted(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret-token")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/agents":
            return _response(200, [{"id": "agent-1"}], request)
        if request.url.path == "/v1/agents/agent-1/runs":
            return _response(200, {"id": "run-1"}, request)
        if request.url.path == "/v1/agents/runs/run-1/events":
            payload = (
                "event: run.completed\n"
                'data: {"output":{"type":"final","payload":{"message":"api_key=super-secret-token"}}}\n\n'
            )
            return _response(200, payload, request)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    provider = ControlPlaneProvider(
        {
            "base_url": "http://control-plane",
            "agent_id": "agent-1",
            "transport": httpx.MockTransport(handler),
        }
    )

    assert "super-secret-token" not in repr(provider)
    response = await provider.chat_completion([{"role": "user", "content": "Fix it"}])
    content = response["choices"][0]["message"]["content"]
    assert "super-secret-token" not in content
    assert "[REDACTED]" in content


@pytest.mark.asyncio
async def test_control_plane_run_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/agents":
            return _response(200, [{"id": "agent-1"}], request)
        if request.url.path == "/v1/agents/agent-1/runs":
            return _response(200, {"id": "run-1"}, request)
        if request.url.path == "/v1/agents/runs/run-1/events":
            payload = 'event: run.failed\ndata: {"message":"provider exploded"}\n\n'
            return _response(200, payload, request)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    provider = ControlPlaneProvider(
        {
            "base_url": "http://control-plane",
            "agent_id": "agent-1",
            "transport": httpx.MockTransport(handler),
        }
    )

    with pytest.raises(RuntimeError, match="provider exploded"):
        await provider.chat_completion([{"role": "user", "content": "Fix it"}])


@pytest.mark.asyncio
async def test_control_plane_sse_malformed_is_ignored():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = (
            "event: tool.called\n"
            "data: not-json\n\n"
            "event: tool.called\n"
            'data: {"tool_name":"final","parameters":{"message":"done"}}\n\n'
        )
        return _response(200, payload, request)

    provider = ControlPlaneProvider(
        {
            "base_url": "http://control-plane",
            "agent_id": "agent-1",
            "transport": httpx.MockTransport(handler),
        }
    )
    events = [event async for event in provider._stream_sse_events("http://control-plane/sse")]
    assert len(events) == 1
    assert events[0]["tool_name"] == "final"


@pytest.mark.asyncio
async def test_control_plane_retry_on_503():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return _response(503, {"error": "busy"}, request)
        return _response(200, [{"id": "agent-1"}], request)

    provider = ControlPlaneProvider(
        {
            "base_url": "http://control-plane",
            "agent_id": "agent-1",
            "max_retries": 1,
            "transport": httpx.MockTransport(handler),
        }
    )

    agents = await provider.list_agents()
    assert agents == [{"id": "agent-1"}]
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_control_plane_no_retry_on_401():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return _response(401, {"error": "nope"}, request)

    provider = ControlPlaneProvider(
        {
            "base_url": "http://control-plane",
            "agent_id": "agent-1",
            "max_retries": 3,
            "transport": httpx.MockTransport(handler),
        }
    )

    with pytest.raises(httpx.HTTPStatusError):
        await provider.list_agents()
    assert attempts["count"] == 1
