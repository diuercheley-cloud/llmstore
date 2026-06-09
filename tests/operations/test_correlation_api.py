import uuid

import pytest
import pytest_asyncio

# Ensure models are registered for tests
from httpx import AsyncClient


@pytest_asyncio.fixture(autouse=True)
async def ensure_correlation_tables(admin_client: AsyncClient):
    # Importar modelos aqui para evitar importações circulares globais
    from app.models.operations.correlation import OperationalCorrelation
    from app.db.base import Base
    from app.db.session import get_db_session
    async for session in get_db_session():
        engine = session.bind
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        break

@pytest.mark.asyncio
class TestCorrelationAPI:
    
    async def test_run_correlation(self, admin_client: AsyncClient, admin_token_headers: dict):
        client_id = str(uuid.uuid4())
        payload = {
            "client_id": client_id,
            "events": [
                {"source_domain": "billing", "event_type": "fail", "severity": "critical", "timestamp": "2026-05-15T10:00:00Z"},
                {"source_domain": "runtime", "event_type": "fail", "severity": "critical", "timestamp": "2026-05-15T10:00:01Z"}
            ]
        }
        
        r = await admin_client.post(
            "/admin/operations/correlations/run",
            json=payload,
            headers=admin_token_headers
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "correlation" in data
        assert "receipt" in data
        assert data["correlation"]["type"] == "cross_domain_impact"
        assert data["receipt"]["advisory_only"] is True

    async def test_list_correlations(self, admin_client: AsyncClient, admin_token_headers: dict):
        client_id = str(uuid.uuid4())
        # First create one
        payload = {
            "client_id": client_id,
            "events": [{"source_domain": "runtime", "event_type": "e", "severity": "info"}]
        }
        await admin_client.post("/admin/operations/correlations/run", json=payload, headers=admin_token_headers)
        
        r = await admin_client.get(
            f"/admin/operations/correlations/?client_id={client_id}",
            headers=admin_token_headers
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert data[0]["client_id"] == client_id

    async def test_build_trust_graph(self, admin_client: AsyncClient, admin_token_headers: dict):
        client_id = str(uuid.uuid4())
        payload = {
            "client_id": client_id,
            "events": [{"source_domain": "runtime", "event_type": "e", "severity": "info"}]
        }
        
        r = await admin_client.post(
            f"/admin/operations/correlations/trust-graph/build?client_id={client_id}",
            json=[{"source_domain": "runtime"}],
            headers=admin_token_headers
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "summary" in data
        assert "receipt" in data
        assert data["summary"]["edge_count"] >= 1

    async def test_correlation_risk_analysis(self, admin_client: AsyncClient, admin_token_headers: dict):
        client_id = str(uuid.uuid4())
        # Create a correlation first
        payload = {
            "client_id": client_id,
            "events": [
                {"source_domain": "billing", "event_type": "fail", "severity": "critical", "timestamp": "2026-05-15T10:00:00Z"},
                {"source_domain": "runtime", "event_type": "fail", "severity": "critical", "timestamp": "2026-05-15T10:00:01Z"}
            ]
        }
        resp = await admin_client.post("/admin/operations/correlations/run", json=payload, headers=admin_token_headers)
        correlation_id = resp.json()["correlation"]["id"]
        
        # Analyze it
        analysis_payload = {
            "client_id": client_id,
            "correlation_id": correlation_id
        }
        r = await admin_client.post(
            "/admin/operations/correlations/correlation-risk-analysis",
            json=analysis_payload,
            headers=admin_token_headers
        )
        assert r.status_code == 200
        data = r.json()
        assert "risk_level" in data
        assert data["advisory_only"] is True
        assert data["dry_run"] is True
