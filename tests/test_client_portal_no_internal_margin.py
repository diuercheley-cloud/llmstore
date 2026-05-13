import os
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_client_portal_no_margin(admin_client: AsyncClient):
    portal_endpoints = [
        "/client-portal",
        "/portal/account",
    ]

    for ep in portal_endpoints:
        resp = await admin_client.get(ep)
        if resp.status_code != 200 and resp.status_code != 404:
            continue
        if resp.status_code == 404:
            continue

        text = resp.text.lower()
        assert "gross_profit" not in text, f"'gross_profit' found in {ep}"
        assert "provider_cost_brl" not in text, f"'provider_cost_brl' found in {ep}"
        assert "margin_percent" not in text, f"'margin_percent' found in {ep}"


@pytest.mark.asyncio
async def test_hybrid_rag_admin_no_internal_pricing(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/rag", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()

    assert "margin_percent" not in data
    assert "provider_cost_brl" not in data
    assert "total_cost" not in data


@pytest.mark.asyncio
async def test_internal_margin_not_in_client_portal_html():
    from pathlib import Path
    candidates = [
        Path("control_plane/app/static/portal/index.html"),
        Path("app/static/portal/index.html"),
    ]
    portal_path = next((p for p in candidates if p.exists()), None)
    if portal_path is None:
        pytest.skip("Client portal HTML not found")

    content = portal_path.read_text().lower()
    assert "gross_profit" not in content
    assert "margin_percent" not in content
    assert "provider_cost_brl" not in content


@pytest.mark.asyncio
async def test_admin_sees_margin(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/summary", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()

    assert "margin_percent" in data
    assert "gross_profit_brl" in data
    assert "provider_cost_brl" in data
