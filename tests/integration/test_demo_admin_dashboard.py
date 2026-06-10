import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_demo_admin_summary(admin_client: AsyncClient, admin_token_headers: dict[str, str]):
    response = await admin_client.get(
        "/admin/demo/summary",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "demo_enabled" in data
    assert "demo_client" in data
    assert "demo_usage" in data
    assert "demo_billing" in data
    assert "demo_rag" in data
    assert "demo_models" in data
    assert "warnings" in data
    assert "is_synthetic" in data

@pytest.mark.asyncio
async def test_admin_usage_summary_enhanced(admin_client: AsyncClient, admin_token_headers: dict[str, str]):
    response = await admin_client.get(
        "/admin/usage/summary",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "totals" in data
    assert "backends_online" in data["totals"]
    assert "backends_total" in data["totals"]
    assert "models_online" in data["totals"]
    assert "models_total" in data["totals"]
    assert "rag" in data
    assert "total_docs" in data["rag"]
    assert "total_storage_mb" in data["rag"]
    assert "total_queries_month" in data["rag"]

@pytest.mark.asyncio
async def test_admin_usage_summary_compact_omits_heavy_lists(admin_client: AsyncClient, admin_token_headers: dict[str, str]):
    response = await admin_client.get(
        "/admin/usage/summary?compact=1",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["clients"] == []
    assert data["models"] == []
    assert data["tts"] == {}
