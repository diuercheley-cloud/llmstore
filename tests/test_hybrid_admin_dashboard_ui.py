import pytest
from pathlib import Path


def _find_dashboard() -> Path:
    candidates = [
        Path("control_plane/app/static/admin/index.html"),
        Path("app/static/admin/index.html"),
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("admin dashboard static file not found")


@pytest.mark.asyncio
async def test_dashboard_contains_hybrid_section():
    path = _find_dashboard()
    content = path.read_text()
    assert "Hybrid AI Platform" in content
    assert "hybridSection" in content
    assert "hybridTotalRequests" in content
    assert "hybridBadge" in content


@pytest.mark.asyncio
async def test_dashboard_contains_providers_section():
    path = _find_dashboard()
    content = path.read_text()
    assert "providersSection" in content
    assert "providersTable" in content
    assert "renderHybridProviders" in content


@pytest.mark.asyncio
async def test_dashboard_contains_routing_section():
    path = _find_dashboard()
    content = path.read_text()
    assert "routingSection" in content
    assert "routingDecisionsTable" in content
    assert "routingStrategy" in content
    assert "renderHybridRouting" in content


@pytest.mark.asyncio
async def test_dashboard_contains_costs_section():
    path = _find_dashboard()
    content = path.read_text()
    assert "costsSection" in content
    assert "costsTable" in content
    assert "renderHybridFinancials" in content


@pytest.mark.asyncio
async def test_dashboard_contains_margin_section():
    path = _find_dashboard()
    content = path.read_text()
    assert "marginSection" in content
    assert "marginTable" in content


@pytest.mark.asyncio
async def test_dashboard_contains_wallet_section():
    path = _find_dashboard()
    content = path.read_text()
    assert "walletSection" in content
    assert "walletTable" in content
    assert "renderHybridWallets" in content


@pytest.mark.asyncio
async def test_dashboard_contains_cache_section():
    path = _find_dashboard()
    content = path.read_text()
    assert "cacheSection" in content
    assert "cacheExactEnabled" in content
    assert "cacheSemanticEnabled" in content
    assert "renderHybridCache" in content


@pytest.mark.asyncio
async def test_dashboard_contains_rag_section():
    path = _find_dashboard()
    content = path.read_text()
    assert "hybridRagSection" in content
    assert "ragEnabled" in content
    assert "ragDocuments" in content
    assert "renderHybridRag" in content


@pytest.mark.asyncio
async def test_dashboard_contains_provider_health_section():
    path = _find_dashboard()
    content = path.read_text()
    assert "providerHealthSection" in content
    assert "providerHealthTable" in content


@pytest.mark.asyncio
async def test_dashboard_fetches_hybrid_endpoints():
    path = _find_dashboard()
    content = path.read_text()
    assert "/admin/hybrid/summary" in content
    assert "/admin/hybrid/providers" in content
    assert "/admin/hybrid/routing" in content
    assert "/admin/hybrid/financials" in content
    assert "/admin/hybrid/cache" in content
    assert "/admin/hybrid/wallets" in content
    assert "/admin/hybrid/rag" in content


@pytest.mark.asyncio
async def test_dashboard_cloud_disabled_appears():
    path = _find_dashboard()
    content = path.read_text()
    assert "CLOUD DISABLED" in content or "CLOUD ENABLED" in content
    assert "cloud_enabled" in content


@pytest.mark.asyncio
async def test_dashboard_no_secrets_exposed():
    path = _find_dashboard()
    content = path.read_text()
    lower = content.lower()
    assert "secret" not in lower or "admin-secret" not in lower
