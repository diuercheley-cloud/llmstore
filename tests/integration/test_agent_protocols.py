import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.services.agents.protocols.service import ProtocolService
from app.services.agents.protocols.base import TrustLevel, ProtocolType
from app.models.agents.agent_mcp_registry import AgentMCPServer


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.mark.asyncio
async def test_list_mcp_servers(mock_db):
    service = ProtocolService(mock_db)
    
    # Mock database return
    mock_server = AgentMCPServer(
        id=uuid.uuid4(),
        tenant_id="test-tenant",
        name="test-server",
        transport="http",
        endpoint="http://localhost:8000",
        trust_level="trusted"
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_server]
    mock_db.execute.return_value = mock_result
    
    servers = await service.list_mcp_servers("test-tenant")
    
    assert len(servers) == 1
    assert servers[0].name == "test-server"
    assert servers[0].trust_level == TrustLevel.TRUSTED


@pytest.mark.asyncio
async def test_dry_run_handshake(mock_db):
    service = ProtocolService(mock_db)
    
    result = await service.dry_run_handshake("http://remote-agent:8080")
    
    assert result["status"] == "success"
    assert "chat" in result["capabilities"]


@pytest.mark.asyncio
async def test_evaluate_trust_decision(mock_db):
    service = ProtocolService(mock_db)
    
    entity_id = uuid.uuid4()
    decision = await service.evaluate_trust(ProtocolType.MCP, entity_id, "tool_call")
    
    assert decision["allowed"] is True
    assert "trusted tenant" in decision["reason"]
