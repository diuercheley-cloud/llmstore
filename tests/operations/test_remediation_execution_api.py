import pytest
import uuid
from httpx import AsyncClient
import pytest_asyncio

# Ensure models are registered for tests
from app.models.operations.remediation_planning import RemediationPlan, RemediationStep
from app.models.operations.remediation_execution import (
    RemediationExecution,
    RemediationExecutionStep,
    RemediationKillSwitchState,
)

@pytest_asyncio.fixture(autouse=True)
async def ensure_execution_tables(admin_client: AsyncClient):
    from app.db.base import Base
    from app.db.session import get_db_session
    async for session in get_db_session():
        engine = session.bind
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        break

@pytest.mark.asyncio
class TestRemediationExecutionAPI:
    async def test_prepare_and_execute_flow(self, admin_client: AsyncClient, admin_token_headers: dict):
        client_id = str(uuid.uuid4())
        
        # 1. Create a plan first (using Phase 71 API)
        plan_payload = {
            "client_id": client_id,
            "source_type": "forecast",
            "source_ref": "f1",
            "risk_level": "low"
        }
        p_resp = await admin_client.post("/admin/operations/remediation-plans/propose", json=plan_payload, headers=admin_token_headers)
        plan_id = p_resp.json()["plan"]["id"]
        
        # 2. Prepare execution
        prep_payload = {"client_id": client_id, "plan_id": plan_id, "dry_run": True}
        prep_resp = await admin_client.post("/admin/operations/remediation-executions/prepare", json=prep_payload, headers=admin_token_headers)
        assert prep_resp.status_code == 200
        exec_id = prep_resp.json()["execution"]["id"]
        
        # 3. Execute
        exec_payload = {"client_id": client_id, "execution_id": exec_id, "dry_run": True}
        run_resp = await admin_client.post("/admin/operations/remediation-executions/execute", json=exec_payload, headers=admin_token_headers)
        assert run_resp.status_code == 200
        assert run_resp.json()["execution"]["status"] == "dry_run_completed"

    async def test_kill_switch_api(self, admin_client: AsyncClient, admin_token_headers: dict):
        client_id = str(uuid.uuid4())
        
        # Enable KS
        ks_payload = {"client_id": client_id, "enabled": True, "reason": "Emergency"}
        r1 = await admin_client.post("/admin/operations/remediation-executions/kill-switch", json=ks_payload, headers=admin_token_headers)
        assert r1.status_code == 200
        assert r1.json()["enabled"] is True
        
        # Get KS
        r2 = await admin_client.get(
            "/admin/operations/remediation-executions/kill-switch", 
            params={"client_id": client_id}, 
            headers=admin_token_headers
        )
        assert r2.status_code == 200, f"Error: {r2.text}"
        assert r2.json()["enabled"] is True
