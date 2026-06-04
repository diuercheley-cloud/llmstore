# Owner: agent-platform
"""
MCP Registry

Per-process in-memory registry of MCP server configurations.

Each server record carries:
  - id, tenant_id, name, transport, endpoint
  - trust_level   : untrusted | low | medium | high | admin
  - approved_tools: admin-curated allowlist of callable tools
  - discovered_tools / resources / prompts : from last discovery run
  - server_info   : populated from MCP initialize response

Thread safety: access is not guarded by a lock because FastAPI routes
run in a single asyncio event loop.  If multi-process deployment is
needed, replace the dict with a Redis/DB-backed store.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.models.agent_mcp_registry import AgentMCPServer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class MCPServerRecord:
    id: str
    tenant_id: str
    name: str
    transport: str          # 'streamable_http' | 'http' | 'stdio'
    endpoint: str
    trust_level: str = "untrusted"
    approved_tools: set[str] = field(default_factory=set)
    discovered_tools: list[dict[str, Any]] = field(default_factory=list)
    discovered_resources: list[dict[str, Any]] = field(default_factory=list)
    discovered_prompts: list[dict[str, Any]] = field(default_factory=list)
    server_info: dict[str, Any] = field(default_factory=dict)


class MCPRegistry:
    # Class-level shared store — survives across request objects in one process
    _servers: dict[str, MCPServerRecord] = {}

    def register(
        self,
        tenant_id: str,
        name: str,
        transport: str,
        endpoint: str,
        trust_level: str = "untrusted",
    ) -> MCPServerRecord:
        server = MCPServerRecord(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            transport=transport,
            endpoint=endpoint,
            trust_level=trust_level,
        )
        self._servers[server.id] = server
        return server

    def list(self, tenant_id: str | None = None) -> list[MCPServerRecord]:
        servers = list(self._servers.values())
        if tenant_id is None:
            return servers
        return [s for s in servers if s.tenant_id == tenant_id]

    def get(self, server_id: str) -> MCPServerRecord | None:
        return self._servers.get(server_id)

    def remove(self, server_id: str) -> bool:
        if server_id in self._servers:
            del self._servers[server_id]
            return True
        return False

    @staticmethod
    def _record_from_model(model: AgentMCPServer) -> MCPServerRecord:
        return MCPServerRecord(
            id=str(model.id),
            tenant_id=model.tenant_id,
            name=model.name,
            transport=model.transport,
            endpoint=model.endpoint,
            trust_level=model.trust_level,
            approved_tools=set(model.approved_tools or []),
            discovered_tools=list(model.discovered_tools or []),
            discovered_resources=list(model.discovered_resources or []),
            discovered_prompts=list(model.discovered_prompts or []),
            server_info=dict(model.server_info or {}),
        )

    async def register_persistent(
        self,
        db: AsyncSession,
        tenant_id: str,
        name: str,
        transport: str,
        endpoint: str,
        trust_level: str = "untrusted",
    ) -> MCPServerRecord:
        server = AgentMCPServer(
            tenant_id=tenant_id,
            name=name,
            transport=transport,
            endpoint=endpoint,
            trust_level=trust_level,
        )
        db.add(server)
        await db.commit()
        await db.refresh(server)
        return self._record_from_model(server)

    async def list_persistent(
        self,
        db: AsyncSession,
        tenant_id: str | None = None,
    ) -> list[MCPServerRecord]:
        stmt = select(AgentMCPServer).order_by(AgentMCPServer.created_at.asc())
        if tenant_id is not None:
            stmt = stmt.where(AgentMCPServer.tenant_id == tenant_id)
        result = await db.execute(stmt)
        return [self._record_from_model(row) for row in result.scalars().all()]

    async def get_persistent(
        self,
        db: AsyncSession,
        server_id: str,
        tenant_id: str | None = None,
    ) -> MCPServerRecord | None:
        stmt = select(AgentMCPServer).where(AgentMCPServer.id == uuid.UUID(server_id))
        if tenant_id is not None:
            stmt = stmt.where(AgentMCPServer.tenant_id == tenant_id)
        result = await db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._record_from_model(model)

    async def approve_tool_persistent(
        self,
        db: AsyncSession,
        server_id: str,
        tool_name: str,
    ) -> MCPServerRecord:
        model = await db.get(AgentMCPServer, uuid.UUID(server_id))
        if model is None:
            raise KeyError(f"MCP server '{server_id}' not found")
        approved = set(model.approved_tools or [])
        approved.add(tool_name)
        model.approved_tools = sorted(approved)
        await db.commit()
        await db.refresh(model)
        return self._record_from_model(model)

    async def update_discovery_persistent(
        self,
        db: AsyncSession,
        server_id: str,
        *,
        discovered_tools: list[dict[str, Any]],
        discovered_resources: list[dict[str, Any]],
        discovered_prompts: list[dict[str, Any]],
        server_info: dict[str, Any],
    ) -> MCPServerRecord:
        model = await db.get(AgentMCPServer, uuid.UUID(server_id))
        if model is None:
            raise KeyError(f"MCP server '{server_id}' not found")
        model.discovered_tools = discovered_tools
        model.discovered_resources = discovered_resources
        model.discovered_prompts = discovered_prompts
        model.server_info = server_info
        await db.commit()
        await db.refresh(model)
        return self._record_from_model(model)
