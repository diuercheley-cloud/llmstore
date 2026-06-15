from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_harness_surface(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    health = await async_client.get("/admin/harness/health", headers=admin_token_headers)
    assert health.status_code == 200
    payload = health.json()
    assert payload["status"] == "healthy"
    assert "max_concurrent_runs" in payload
    assert "active_runs" in payload
    assert "active_eval_runs" in payload
    assert payload["runtime_available"] is True

    providers = await async_client.get("/admin/harness/providers", headers=admin_token_headers)
    assert providers.status_code == 200
    assert "providers" in providers.json()

    tools = await async_client.get("/admin/harness/tools", headers=admin_token_headers)
    assert tools.status_code == 200
    tools_json = tools.json()
    assert any(tool["name"] == "run_shell" for tool in tools_json["tools"])


@pytest.mark.asyncio
async def test_harness_health_details(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.get("/admin/harness/health", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert isinstance(data["active_runs"], int)
    assert isinstance(data["active_eval_runs"], int)
    assert isinstance(data["max_concurrent_runs"], int)
    assert data["max_concurrent_runs"] == 4
    assert "runtime_error" in data


@pytest.mark.asyncio
async def test_harness_tools_list_structure(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.get("/admin/harness/tools", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert isinstance(data["tools"], list)
    required = {"plan", "read_file", "grep", "find_replace", "run_shell", "final"}
    names = {t["name"] for t in data["tools"]}
    assert required.issubset(names), f"Missing tools: {required - names}"
    for tool in data["tools"]:
        assert "name" in tool
        assert "description" in tool


@pytest.mark.asyncio
async def test_harness_providers_list(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.get("/admin/harness/providers", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert isinstance(data["providers"], list)


@pytest.mark.asyncio
async def test_harness_provider_models_requires_base_url(
    async_client, admin_token_headers, monkeypatch
):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.get(
        "/admin/harness/providers/local-openai-compatible/models",
        headers=admin_token_headers,
    )
    assert response.status_code == 422
    assert "base_url" in response.json()["detail"]


@pytest.mark.asyncio
async def test_harness_provider_models_success(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)

    agent = AsyncMock()
    agent.health_check.return_value = {
        "status": "healthy",
        "details": {
            "available_models": ["nvidia/nemotron-3-nano-4b"],
            "selected_model": "nvidia/nemotron-3-nano-4b",
            "models_url": "http://127.0.0.1:1234/v1/models",
            "supports_native_tool_calling": False,
            "auto_selected_model": False,
        },
    }
    monkeypatch.setattr("app.api.harness.create_code_agent", lambda provider, config: agent)

    response = await async_client.get(
        "/admin/harness/providers/local-openai-compatible/models?base_url=http://127.0.0.1:1234/v1&model=nvidia/nemotron-3-nano-4b",
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "local-openai-compatible"
    assert data["models"] == ["nvidia/nemotron-3-nano-4b"]
    assert data["selected_model"] == "nvidia/nemotron-3-nano-4b"


@pytest.mark.asyncio
async def test_harness_evals_list(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.get("/admin/harness/evals", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "eval_suites" in data
    assert isinstance(data["eval_suites"], list)


@pytest.mark.asyncio
async def test_harness_runs_empty(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.get("/admin/harness/runs", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert isinstance(data["runs"], list)


@pytest.mark.asyncio
async def test_harness_run_not_found(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.get(
        "/admin/harness/runs/non-existent-id", headers=admin_token_headers
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_harness_cancel_nonexistent_run(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.post(
        "/admin/harness/runs/non-existent-id/cancel", headers=admin_token_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_harness_delete_nonexistent_run(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.delete(
        "/admin/harness/runs/non-existent-id", headers=admin_token_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_harness_events_stream_nonexistent(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.get(
        "/admin/harness/runs/non-existent-id/events", headers=admin_token_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_harness_page_is_unauthed(async_client):
    """The /harness page itself is public (served as a static file)."""
    response = await async_client.get("/harness")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_harness_page_is_served(async_client):
    response = await async_client.get("/harness")
    assert response.status_code == 200
    assert "LLM Harness" in response.text


@pytest.mark.asyncio
async def test_harness_page_has_required_elements(async_client):
    response = await async_client.get("/harness")
    html = response.text
    assert 'id="admin-token"' in html
    assert 'id="clear-token-btn"' in html
    assert 'id="run-btn"' in html
    assert 'id="cancel-btn"' in html
    assert 'id="eval-btn"' in html
    assert 'id="refresh-btn"' in html
    assert 'id="task"' in html
    assert 'id="provider"' in html
    assert 'id="cfg-base-url"' in html
    assert 'id="cfg-local-timeout"' in html
    assert 'id="cfg-tool-calling"' in html
    assert 'id="cfg-stream"' in html
    assert 'id="cfg-auto-timeout"' in html
    assert 'id="provider-hint"' in html
    assert 'id="eval-suite"' in html
    assert 'id="events"' in html
    assert 'id="run-output"' in html


@pytest.mark.asyncio
async def test_harness_page_catch_all(async_client):
    response = await async_client.get("/harness/some/path")
    assert response.status_code == 200
    assert "LLM Harness" in response.text


@pytest.mark.asyncio
async def test_run_request_validation_empty_task(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.post(
        "/admin/harness/runs",
        json={"task": ""},
        headers=admin_token_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_run_request_validation_too_long_task(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.post(
        "/admin/harness/runs",
        json={"task": "x" * 100_001},
        headers=admin_token_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_eval_request_validation(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.post(
        "/admin/harness/evals/runs",
        json={"suite_path": ""},
        headers=admin_token_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_eval_request_invalid_concurrency(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.post(
        "/admin/harness/evals/runs",
        json={"suite_path": "test.json", "concurrency": 0},
        headers=admin_token_headers,
    )
    assert response.status_code == 422

    response = await async_client.post(
        "/admin/harness/evals/runs",
        json={"suite_path": "test.json", "concurrency": 9},
        headers=admin_token_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_run_request_validation_local_provider_requires_base_url(
    async_client, admin_token_headers, monkeypatch
):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.post(
        "/admin/harness/runs",
        json={"task": "test task", "provider": "local-openai-compatible", "config_overrides": {}},
        headers=admin_token_headers,
    )
    assert response.status_code == 422
    assert "base_url" in str(response.json())


@pytest.mark.asyncio
async def test_eval_request_validation_local_provider_requires_base_url(
    async_client, admin_token_headers, monkeypatch
):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.post(
        "/admin/harness/evals/runs",
        json={
            "suite_path": "test.json",
            "provider": "local-openai-compatible",
            "config_overrides": {},
        },
        headers=admin_token_headers,
    )
    assert response.status_code == 422
    assert "base_url" in str(response.json())


@pytest.mark.asyncio
async def test_harness_run_request_with_tags(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.post(
        "/admin/harness/runs",
        json={"task": "test task", "tags": ["test", "ci"]},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "running"


@pytest.mark.asyncio
async def test_harness_run_request_with_webhook(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.post(
        "/admin/harness/runs",
        json={"task": "test task", "webhook_url": "https://example.com/hook"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "running"


@pytest.mark.asyncio
async def test_harness_list_runs_pagination(async_client, admin_token_headers, monkeypatch):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.get(
        "/admin/harness/runs?limit=5&offset=0", headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert isinstance(data["runs"], list)


@pytest.mark.asyncio
async def test_harness_eval_events_stream_nonexistent(
    async_client, admin_token_headers, monkeypatch
):
    monkeypatch.setattr("app.services.auth.is_rbac_admin_enabled", lambda: False)
    response = await async_client.get(
        "/admin/harness/evals/runs/non-existent-id/events", headers=admin_token_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_harness_page_has_new_elements(async_client):
    response = await async_client.get("/harness")
    html = response.text
    assert 'id="preset-select"' in html
    assert 'id="tags-input"' in html
    assert 'id="webhook-url"' in html
    assert 'id="batch-tasks"' in html
    assert 'id="toast-container"' in html
    assert 'id="modal-root"' in html
    assert 'id="slash-menu"' in html
    assert 'id="chart-toggle"' in html
    assert 'id="trace-count-badge"' in html
    assert 'id="save-preset-btn"' in html
    assert 'data-theme="dark"' not in html or "data-theme=" in html
    assert "prefers-color-scheme" in html
    assert "AbortController" in html
    assert "showModal" in html
    assert "SLASH_COMMANDS" in html
