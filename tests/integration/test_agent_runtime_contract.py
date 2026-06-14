import pytest
import uuid
from unittest.mock import AsyncMock, patch
from app.services.agents.agent_runtime_client import AgentRuntimeClient
from services.agent_runtime.app.schemas.contract import AgentRunStartRequest, AgentRunResponse

@pytest.mark.asyncio
async def test_client_in_process_mode(session):
    """Verifica que o cliente funciona corretamente no modo legado (in-process)."""
    with patch("app.services.agents.agent_runtime_client.settings") as mock_settings:
        mock_settings.agent_runtime_service_remote = False
        
        client = AgentRuntimeClient()
        assert client.is_remote is False
        
        agent_id = uuid.uuid4()
        tenant_id = "test-tenant"
        
        # Mock internal_runtime.start_run
        with patch("app.services.agents.agent_runtime.start_run", new_callable=AsyncMock) as mock_start:
            mock_run = MagicMock()
            mock_run.id = uuid.uuid4()
            mock_start.return_value = mock_run
            
            res = await client.start_run(session, agent_id, tenant_id, "hello")
            assert res == mock_run
            mock_start.assert_called_once()

@pytest.mark.asyncio
async def test_client_remote_mode_contract():
    """Verifica que o cliente respeita o contrato REST no modo remoto."""
    with patch("app.services.agents.agent_runtime_client.settings") as mock_settings:
        mock_settings.agent_runtime_service_remote = True
        mock_settings.agent_runtime_service_url = "http://mock-service"
        mock_settings.agent_runtime_service_token = "secret"
        
        client = AgentRuntimeClient()
        
        agent_id = uuid.uuid4()
        run_id = uuid.uuid4()
        
        # Mock httpx response
        mock_resp_data = {
            "id": str(run_id),
            "agent_id": str(agent_id),
            "tenant_id": "t1",
            "status": "queued",
            "created_at": "2026-06-11T20:00:00Z"
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_resp_data
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response
            
            res = await client.start_run(None, agent_id, "t1", "hi")
            
            assert res["id"] == str(run_id)
            assert res["status"] == "queued"
            
            # Verify request payload contract
            args, kwargs = mock_post.call_args
            payload = kwargs["json"]
            AgentRunStartRequest(**payload) # Should not raise validation error

from unittest.mock import MagicMock
