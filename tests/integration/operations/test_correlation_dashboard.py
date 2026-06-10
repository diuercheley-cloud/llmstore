import uuid

import pytest
import pytest_asyncio
from app.models.operations.correlation import OperationalCorrelation
from httpx import AsyncClient


@pytest_asyncio.fixture
async def portal_client_data(admin_client: AsyncClient, admin_token_headers):
    # Create a client
    resp = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "Portal Test Client", "rate_limit_per_minute": 10}
    )
    client_data = resp.json()
    client_id = client_data["id"]
    
    # Create an API key for the client
    resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": client_id, "name": "Portal Test Key"}
    )
    key_data = resp.json()
    return {"id": client_id, "api_key": key_data["api_key"]}

@pytest.fixture
def client_token_headers(portal_client_data):
    return {"Authorization": f"Bearer {portal_client_data['api_key']}"}

@pytest.mark.asyncio
class TestCorrelationDashboard:
    
    async def test_portal_list_correlations(self, admin_client: AsyncClient, client_token_headers: dict, portal_client_data: dict):
        # Setup: Create some correlations for this client
        from app.db.session import get_db_session
        async for session in get_db_session():
            correlation = OperationalCorrelation(
                client_id=uuid.UUID(portal_client_data["id"]),
                correlation_type="test_correlation",
                source_domains_json=["domain1", "domain2"],
                correlation_key="test_key",
                correlation_score=0.85,
                confidence=0.9,
                advisory_only=True,
                immutable_hash=uuid.uuid4().hex
            )
            session.add(correlation)
            await session.commit()
            break
        
        # Test portal endpoint
        r = await admin_client.get("/portal/operations/correlations/", headers=client_token_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert data[0]["correlation_type"] == "test_correlation"
        assert data[0]["correlation_score"] == 0.85
        assert "immutable_hash" in data[0]

    async def test_portal_trust_graph_summary(self, admin_client: AsyncClient, client_token_headers: dict):
        r = await admin_client.get("/portal/operations/correlations/trust-graph", headers=client_token_headers)
        assert r.status_code == 200
        data = r.json()
        # Trust graph might be empty but the endpoint should return a structure
        assert "node_count" in data or "total_nodes" in data or "nodes" in data

    async def test_admin_correlation_dashboard_data(self, admin_client: AsyncClient, admin_token_headers: dict):
        # Verify admin can still list correlations with client_id
        client_id = str(uuid.uuid4())
        r = await admin_client.get(f"/admin/operations/correlations/?client_id={client_id}", headers=admin_token_headers)
        assert r.status_code == 200
        
    async def test_security_portal_isolation(self, admin_client: AsyncClient, client_token_headers: dict):
        # Create correlation for ANOTHER client
        other_client_id = uuid.uuid4()
        
        from app.db.session import get_db_session
        async for session in get_db_session():
            correlation = OperationalCorrelation(
                client_id=other_client_id,
                correlation_type="other_correlation",
                source_domains_json=["other"],
                correlation_key="other_key",
                correlation_score=0.5,
                confidence=0.5,
                advisory_only=True,
                immutable_hash=uuid.uuid4().hex
            )
            session.add(correlation)
            await session.commit()
            break
        
        # Current client should NOT see it
        r = await admin_client.get("/portal/operations/correlations/", headers=client_token_headers)
        assert r.status_code == 200
        data = r.json()
        for c in data:
            assert c["correlation_type"] != "other_correlation"
