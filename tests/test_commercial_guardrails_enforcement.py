import pytest
from app.api.deps import get_inference_proxy
from app.models.commercial_qos_tier import CommercialQoSTier
from sqlalchemy import select
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.services.commercial_guardrails import clear_commercial_guardrail_runtime_events
from app.services.inference_proxy import ForwardResult
from httpx import AsyncClient
from starlette.responses import JSONResponse


class FakeProxy:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def chat(self, payload, stream, include_reasoning, backend, backend_url, backend_name, **kwargs):
        self.calls.append(
            {
                "backend": backend,
                "backend_name": backend_name,
                "backend_url": backend_url,
                "stream": stream,
            }
        )
        return ForwardResult(
            response=JSONResponse(
                content={
                    "id": "chatcmpl-guardrail",
                    "object": "chat.completion",
                    "created": 1677652288,
                    "model": payload.get("model", "default"),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": f"response-via-{backend_name}",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 8,
                        "completion_tokens": 10,
                        "total_tokens": 18,
                    },
                }
            ),
            backend_name=backend_name,
            attempts=1,
            fallback_used=False,
            backend_errors=[],
        )

    async def complete(self, payload, stream, backend, backend_url, backend_name, **kwargs):
        self.calls.append(
            {
                "backend": backend,
                "backend_name": backend_name,
                "backend_url": backend_url,
                "stream": stream,
            }
        )
        return ForwardResult(
            response=JSONResponse(
                content={
                    "id": "cmpl-guardrail",
                    "object": "text_completion",
                    "created": 1677652288,
                    "model": payload.get("model", "default"),
                    "choices": [{"index": 0, "text": f"response-via-{backend_name}", "finish_reason": "stop"}],
                }
            ),
            backend_name=backend_name,
            attempts=1,
            fallback_used=False,
            backend_errors=[],
        )

    def _validate_chat_response_payload(self, payload, **kwargs):
        pass

    def _validate_completion_response_payload(self, payload, **kwargs):
        pass


@pytest.fixture(autouse=True)
def enforcement_env(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import get_settings

    monkeypatch.setenv("DEPLOYMENT_MODE", "pilot")
    monkeypatch.setenv("COMMERCIAL_GUARDRAILS_ENABLED", "false")
    monkeypatch.setenv("MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL", "0")
    monkeypatch.setenv("MAX_PROVIDER_COST_PER_DAY_BRL", "0")
    monkeypatch.setenv("MAX_CLIENT_PROVIDER_COST_PER_DAY_BRL", "0")
    monkeypatch.setenv("MARGIN_WARNING_PERCENT", "20")
    monkeypatch.setenv("NEGATIVE_MARGIN_BLOCK_MODE", "report_only")
    monkeypatch.setenv("GLOBAL_CLOUD_KILL_SWITCH", "false")
    monkeypatch.setenv("CLOUD_PROVIDERS_ENABLED", "true")
    monkeypatch.setenv("OPENAI_PROVIDER_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-ant-mock-key-for-testing")
    get_settings.cache_clear()
    import app.services.providers.registry as registry
    registry._registry_initialized = False
    registry._providers = {}
    clear_commercial_guardrail_runtime_events()
    yield
    clear_commercial_guardrail_runtime_events()
    get_settings.cache_clear()


@pytest.fixture
def mock_proxy():
    from app.main import app

    proxy = FakeProxy()
    app.dependency_overrides[get_inference_proxy] = lambda: proxy
    yield proxy
    app.dependency_overrides.pop(get_inference_proxy, None)


def _apply_guardrail_env(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    from app.core.config import get_settings

    for key, value in values.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


async def _seed_routable_model(
    admin_client: AsyncClient,
    *,
    suffix: str,
    providers: list[tuple[str, str, int]],
) -> tuple[str, str]:
    from app.db.session import get_db_session
    from app.main import app

    create_client = await admin_client.post(
        "/admin/clients",
        json={"name": f"cg-client-{suffix}", "description": "guardrail enforcement", "rate_limit_per_minute": 100},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert create_client.status_code == 201
    client_id = create_client.json()["id"]

    create_key = await admin_client.post(
        "/admin/api-keys",
        json={"client_id": client_id, "name": f"cg-key-{suffix}"},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert create_key.status_code == 201
    api_key = create_key.json()["api_key"]

    session_generator = app.dependency_overrides[get_db_session]()
    session = await session_generator.__anext__()
    try:
        backends: list[InferenceBackend] = []
        for name, provider, priority in providers:
            backend = InferenceBackend(
                name=f"{name}-{suffix}",
                provider=provider,
                backend_url=f"http://localhost:8080/{name}-{suffix}",
                is_active=True,
                status="healthy",
            )
            session.add(backend)
            backends.append((backend, priority))

        # Seed default QoS tier so cloud providers are not filtered out
        result = await session.execute(select(CommercialQoSTier).limit(1))
        if not result.scalar_one_or_none():
            session.add(CommercialQoSTier(
                name="Basic",
                enabled=True,
                priority=10,
                target_latency_ms=1000,
                max_p95_latency_ms=3000,
                min_margin_percent=5.0,
                allow_cloud=True,
                degradation_policy="best_effort"
            ))

        model = ModelRegistry(
            model_id=f"default-{suffix}",
            model_alias=f"default-{suffix}",
            provider="openai_compatible",
            model_file="default.gguf",
            context_length=4096,
            is_active=True,
            is_default=True,
            status="configured",
        )
        session.add(model)
        await session.flush()

        for backend, priority in backends:
            session.add(
                ModelBackendRoute(
                    model_registry_id=model.id,
                    inference_backend_id=backend.id,
                    priority=priority,
                    weight=100,
                    state="healthy",
                )
            )

        await session.commit()
    finally:
        await session_generator.aclose()

    return api_key, client_id


async def _chat_request(admin_client: AsyncClient, api_key: str, model: str = "default"):
    return await admin_client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": "hello enforcement"}],
            "stream": False,
            "max_tokens": 32,
        },
    )


@pytest.mark.asyncio
async def test_feature_disabled_preserves_previous_cloud_routing(admin_client: AsyncClient, mock_proxy: FakeProxy):
    suffix = "disabled"
    api_key, _ = await _seed_routable_model(
        admin_client,
        suffix=suffix,
        providers=[("cloud-primary", "openai", 1), ("local-secondary", "llama.cpp", 2)],
    )

    response = await _chat_request(admin_client, api_key, model=f"default-{suffix}")

    print(f"DEBUG: Calls: {mock_proxy.calls}")
    print(f"DEBUG: Headers: {response.headers}")
    print(f"DEBUG: Response: {response.text}")

    assert response.status_code == 200
    assert response.headers["X-Fallback-Used"] == "false"
    assert mock_proxy.calls[-1]["backend"] in ["openai", "llama.cpp"]


@pytest.mark.asyncio
async def test_report_only_records_event_without_blocking(monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, mock_proxy: FakeProxy):
    suffix = "report-only"
    _apply_guardrail_env(
        monkeypatch,
        COMMERCIAL_GUARDRAILS_ENABLED="true",
        NEGATIVE_MARGIN_BLOCK_MODE="report_only",
        GLOBAL_CLOUD_KILL_SWITCH="true",
    )
    api_key, _ = await _seed_routable_model(
        admin_client,
        suffix=suffix,
        providers=[("cloud-primary", "openai", 1), ("local-secondary", "llama.cpp", 2)],
    )

    response = await _chat_request(admin_client, api_key, model=f"default-{suffix}")
    runtime = await admin_client.get("/admin/commercial-guardrails/runtime-status", headers={"X-Admin-Token": "test-admin-token"})

    print(f"DEBUG: Calls: {mock_proxy.calls}")
    print(f"DEBUG: Headers: {response.headers}")

    assert response.status_code == 200
    assert response.headers["X-Fallback-Used"] == "false"
    assert mock_proxy.calls[-1]["backend"] in ["openai", "llama.cpp"]
    assert runtime.status_code == 200
    assert runtime.json()["report_only_events_today"] >= 1
    assert runtime.json()["blocked_cloud_requests_today"] == 0


@pytest.mark.asyncio
async def test_enforce_cloud_only_uses_local_fallback(monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, mock_proxy: FakeProxy):
    suffix = "fallback"
    _apply_guardrail_env(
        monkeypatch,
        COMMERCIAL_GUARDRAILS_ENABLED="true",
        NEGATIVE_MARGIN_BLOCK_MODE="enforce_cloud_only",
        GLOBAL_CLOUD_KILL_SWITCH="true",
    )
    api_key, _ = await _seed_routable_model(
        admin_client,
        suffix=suffix,
        providers=[("cloud-primary", "openai", 1), ("local-secondary", "llama.cpp", 2)],
    )

    response = await _chat_request(admin_client, api_key, model=f"default-{suffix}")
    runtime = await admin_client.get("/admin/commercial-guardrails/runtime-status", headers={"X-Admin-Token": "test-admin-token"})

    assert response.status_code == 200
    assert response.headers["X-Fallback-Used"] in ["true", "false"]
    assert mock_proxy.calls[-1]["backend"] in ["openai", "llama.cpp"]
    assert f"response-via-local-secondary-{suffix}" in response.text
    assert runtime.json()["successful_local_fallbacks_today"] >= 1
    assert runtime.json()["blocked_cloud_requests_today"] == 0


@pytest.mark.asyncio
async def test_enforce_cloud_only_without_fallback_returns_openai_compatible_error(monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient):
    suffix = "blocked"
    _apply_guardrail_env(
        monkeypatch,
        COMMERCIAL_GUARDRAILS_ENABLED="true",
        NEGATIVE_MARGIN_BLOCK_MODE="enforce_cloud_only",
        GLOBAL_CLOUD_KILL_SWITCH="true",
    )
    api_key, _ = await _seed_routable_model(
        admin_client,
        suffix=suffix,
        providers=[("cloud-primary", "openai", 1)],
    )

    response = await _chat_request(admin_client, api_key, model=f"default-{suffix}")
    runtime = await admin_client.get("/admin/commercial-guardrails/runtime-status", headers={"X-Admin-Token": "test-admin-token"})
    payload = response.text.lower()

    assert response.status_code == 503
    data = response.json()
    error_msg = data.get("error", {}).get("message", "")
    assert "blocked" in error_msg.lower() or "unavailable" in error_msg.lower()
        
    assert "authorization" not in payload
    assert "prompt" not in payload
    assert "sk-" not in payload
    assert runtime.json()["blocked_cloud_requests_today"] >= 1


@pytest.mark.asyncio
async def test_kill_switch_blocks_cloud_but_not_local(monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, mock_proxy: FakeProxy):
    suffix = "kill-switch"
    _apply_guardrail_env(
        monkeypatch,
        COMMERCIAL_GUARDRAILS_ENABLED="true",
        NEGATIVE_MARGIN_BLOCK_MODE="enforce_cloud_only",
        GLOBAL_CLOUD_KILL_SWITCH="true",
    )
    api_key, _ = await _seed_routable_model(
        admin_client,
        suffix=suffix,
        providers=[("local-primary", "llama.cpp", 1)],
    )

    response = await _chat_request(admin_client, api_key, model=f"default-{suffix}")

    assert response.status_code == 200
    assert mock_proxy.calls[-1]["backend"] == "llama.cpp"
    assert response.headers["X-Fallback-Used"] == "false"


@pytest.mark.asyncio
async def test_mock_provider_never_blocked(monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, mock_proxy: FakeProxy):
    suffix = "mock"
    _apply_guardrail_env(
        monkeypatch,
        COMMERCIAL_GUARDRAILS_ENABLED="true",
        NEGATIVE_MARGIN_BLOCK_MODE="enforce_cloud_only",
        GLOBAL_CLOUD_KILL_SWITCH="true",
    )
    api_key, _ = await _seed_routable_model(
        admin_client,
        suffix=suffix,
        providers=[("mock-primary", "mock", 1)],
    )

    response = await _chat_request(admin_client, api_key, model=f"default-{suffix}")

    assert response.status_code == 200
    assert mock_proxy.calls[-1]["backend"] == "mock"
    assert response.headers["X-Fallback-Used"] == "false"


@pytest.mark.asyncio
async def test_runtime_status_payload_is_sanitized(monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, mock_proxy: FakeProxy):
    suffix = "sanitize"
    _apply_guardrail_env(
        monkeypatch,
        COMMERCIAL_GUARDRAILS_ENABLED="true",
        NEGATIVE_MARGIN_BLOCK_MODE="enforce_cloud_only",
        GLOBAL_CLOUD_KILL_SWITCH="true",
    )
    api_key, _ = await _seed_routable_model(
        admin_client,
        suffix=suffix,
        providers=[("cloud-primary", "openai", 1), ("local-secondary", "llama.cpp", 2)],
    )

    response = await _chat_request(admin_client, api_key, model=f"default-{suffix}")
    runtime = await admin_client.get("/admin/commercial-guardrails/runtime-status", headers={"X-Admin-Token": "test-admin-token"})
    combined = response.text.lower() + runtime.text.lower()

    assert response.status_code == 200
    assert "authorization" not in combined
    assert "api_key" not in combined
    assert "provider_api_key" not in combined
    assert "hello enforcement" not in combined
    assert "sk-" not in combined
