import os

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_providers_api_no_full_api_keys(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/providers", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()

    for p in data:
        key = p.get("masked_api_key")
        if key and key != "****":
            assert "****" in key, f"API key for {p['provider_id']} is not masked"
            assert len(key) <= 12, f"Masked key for {p['provider_id']} is too long: {key}"


@pytest.mark.asyncio
async def test_summary_no_sensitive_fields(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/summary", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    text = resp.text.lower()

    assert "api_key" not in text or "masked_api_key" not in text
    assert "secret" not in text
    assert "password" not in text
    assert "token_hash" not in text


@pytest.mark.asyncio
async def test_routing_no_prompts_or_responses(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/routing", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    text = resp.text.lower()

    assert "prompt" not in text
    assert '"messages"' not in text
    assert '"content"' not in text or "role" not in text


@pytest.mark.asyncio
async def test_rag_no_document_content(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/rag", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    text = resp.text.lower()

    assert "original_filename" not in text
    assert "storage_path" not in text
    assert "file_path" not in text
    assert "rag_storage_dir" not in text


@pytest.mark.asyncio
async def test_financials_no_client_level_detail(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/financials", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()

    for pc in data.get("provider_costs", []):
        assert "client_id" not in pc
        assert "client_name" not in pc


@pytest.mark.asyncio
async def test_wallets_no_raw_balance_breakdown_per_client(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/wallets", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()

    for w in data:
        assert isinstance(w.get("balance_brl"), (int, float))
        assert isinstance(w.get("available_brl"), (int, float))
