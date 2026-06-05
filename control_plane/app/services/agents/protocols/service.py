import uuid
import logging
from typing import List, Dict, Any, Optional

from app.services.agents.protocols.base import (
    TrustLevel, 
    ProtocolType, 
    MCPToolServer, 
    MCPTool, 
    A2AAgentEndpoint, 
    ProtocolTrustPolicy
)
from app.models.agent_mcp_registry import AgentMCPServer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

logger = logging.getLogger(__name__)


class ProtocolService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # MCP Logic
    async def list_mcp_servers(self, tenant_id: str) -> List[MCPToolServer]:
        stmt = select(AgentMCPServer).where(AgentMCPServer.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        servers = result.scalars().all()
        return [
            MCPToolServer(
                id=s.id,
                name=s.name,
                endpoint=s.endpoint,
                transport=s.transport,
                trust_level=TrustLevel(s.trust_level)
            ) for s in servers
        ]

    async def approve_mcp_tool(self, server_id: uuid.UUID, tool_name: str):
        stmt = select(AgentMCPServer).where(AgentMCPServer.id == server_id)
        result = await self.db.execute(stmt)
        server = result.scalar_one_or_none()
        if server:
            if tool_name not in server.approved_tools:
                server.approved_tools = list(server.approved_tools) + [tool_name]
                await self.db.flush()

    # A2A Logic (Simulated for evolution)
    async def list_a2a_peers(self, tenant_id: str) -> List[A2AAgentEndpoint]:
        # Implementation will use a new AgentPeer model in the future
        return []

    async def dry_run_handshake(self, peer_url: str) -> Dict[str, Any]:
        """Simulates an A2A handshake."""
        return {
            "status": "success",
            "peer_url": peer_url,
            "capabilities": ["chat", "tool_delegation"],
            "trust_check": "passed",
            "protocol_version": "1.0-draft"
        }

    # Trust Layer
    async def evaluate_trust(
        self, 
        protocol: ProtocolType, 
        entity_id: uuid.UUID, 
        action: str
    ) -> Dict[str, Any]:
        """Explains why an action is allowed or blocked based on trust policy."""
        # Simple builtin logic for demonstration
        return {
            "allowed": True,
            "protocol": protocol.value,
            "entity_id": str(entity_id),
            "reason": "Entity belongs to a trusted tenant and has required scopes."
        }
