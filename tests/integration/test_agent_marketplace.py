import uuid

import pytest
import pytest_asyncio
from app.schemas.marketplace import AgentManifest
from app.services.marketplace.service import MarketplaceService
from app.models.agents.agent_marketplace import MarketplacePublisher

@pytest_asyncio.fixture
async def mock_publisher(session):
    pub = MarketplacePublisher(
        tenant_id="pub-tenant-1",
        name="Trusted Publisher",
        is_verified=True
    )
    session.add(pub)
    await session.commit()
    return pub

@pytest.mark.asyncio
async def test_manifest_validation():
    service = MarketplaceService(None)
    valid_data = {
        "name": "Test Agent",
        "version": "1.2.3",
        "author": "Kleber AI",
        "description": "Safe agent",
        "permissions": ["chat:read"]
    }
    manifest = await service.validate_package(valid_data)
    assert manifest.name == "Test Agent"
    assert "chat:read" in manifest.permissions

@pytest.mark.asyncio
async def test_install_dry_run_dangerous_permissions():
    service = MarketplaceService(None)
    manifest = AgentManifest(
        name="Danger Agent",
        version="1.0.0",
        author="Unknown",
        description="I want your files",
        permissions=["filesystem:write"]
    )
    
    res = await service.install_dry_run(manifest, "https://danger.zone/agent.stack")
    assert res.policy_evaluation == "needs_review"
    assert any("Dangerous permission" in w for w in res.warnings)

@pytest.mark.asyncio
async def test_install_dry_run_unsigned_package():
    service = MarketplaceService(None)
    manifest = AgentManifest(
        name="Unsigned Agent",
        version="1.0.0",
        author="Dev",
        description="No signature here",
        permissions=[],
        signature=None
    )
    
    res = await service.install_dry_run(manifest, "local://unsigned.stack")
    assert res.attestation_verified is False
    assert any("unsigned" in w for w in res.warnings)

@pytest.mark.asyncio
async def test_marketplace_api_flow(admin_client, session, mock_publisher):
    headers = {"X-Admin-Token": "test-admin-token"}
    service = MarketplaceService(session)
    
    # 1. Register an item
    manifest = AgentManifest(
        name="Market API Agent",
        version="1.0.0",
        author="Kleber AI",
        description="Test from API",
        permissions=["web:search"]
    )
    item = await service.register_item(str(mock_publisher.id), manifest)
    await session.commit()
    
    # 2. List agents
    resp = await admin_client.get("/api/admin/marketplace/agents", headers=headers)
    assert resp.status_code == 200
    agents = resp.json()
    assert any(a["name"] == "Market API Agent" for a in agents)
    
    # 3. Dry-run install
    payload = {"package_url": "https://market.stack/agent-api.stack"}
    resp_dry = await admin_client.post("/api/admin/marketplace/install/dry-run", json=payload, headers=headers)
    assert resp_dry.status_code == 200
    assert resp_dry.json()["policy_evaluation"] == "allowed" # Mock default is safe
    
    # 4. Dry-run install (dangerous)
    payload_danger = {"package_url": "https://market.stack/dangerous-agent.stack"}
    resp_danger = await admin_client.post("/api/admin/marketplace/install/dry-run", json=payload_danger, headers=headers)
    assert resp_danger.status_code == 200
    assert resp_danger.json()["policy_evaluation"] == "needs_review"
