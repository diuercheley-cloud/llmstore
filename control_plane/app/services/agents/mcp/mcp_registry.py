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
