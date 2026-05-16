import pytest
import uuid
from httpx import AsyncClient

# Ensure models are registered for tests
from app.models.operations.remediation_planning import (
    RemediationPlan,
    RemediationStep,
    RemediationPlanReceipt,
    RemediationApprovalRequirement,
)
import pytest_asyncio

@pytest_asyncio.fixture(autouse=True)
async def ensure_remediation_tables(admin_client: AsyncClient):
    from app.db.base import Base
    from app.db.session import get_db_session
    async for session in get_db_session():
        engine = session.bind
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        break

@pytest.mark.asyncio
class TestRemediationPlanningAPI:
    async def test_propose_plan_endpoint(self, admin_client: AsyncClient, admin_token_headers: dict):
        client_id = str(uuid.uuid4())
        payload = {
            "client_id": client_id,
            "source_type": "forecast",
            "source_ref": "f123",
            "risk_level": "high",
            "involved_domains": ["auth", "billing"]
        }
        response = await admin_client.post(
            "/admin/operations/remediation-plans/propose",
            json=payload,
            headers=admin_token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "plan" in data
        assert data["plan"]["risk_level"] == "high"
        assert len(data["steps"]) > 0
        assert "explanation" in data

    async def test_list_plans_endpoint(self, admin_client: AsyncClient, admin_token_headers: dict):
        client_id = str(uuid.uuid4())
        response = await admin_client.get(
            f"/admin/operations/remediation-plans/?client_id={client_id}",
            headers=admin_token_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_generate_receipt_endpoint(self, admin_client: AsyncClient, admin_token_headers: dict):
        client_id = str(uuid.uuid4())
        # First propose a plan
        propose_payload = {
            "client_id": client_id,
            "source_type": "correlation",
            "source_ref": "c456",
            "risk_level": "low"
        }
        p_resp = await admin_client.post(
            "/admin/operations/remediation-plans/propose",
            json=propose_payload,
            headers=admin_token_headers
        )
        plan_id = p_resp.json()["plan"]["id"]
        
        # Then generate receipt
        response = await admin_client.post(
            f"/admin/operations/remediation-plans/{plan_id}/receipt",
            headers=admin_token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["receipt_type"] == "remediation_plan_proposal"
        assert "immutable_hash" in data
