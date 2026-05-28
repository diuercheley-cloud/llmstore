# Owner: agent-platform
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import require_admin
from app.core.config import Settings, get_settings
from app.services.agents.mcp.mcp_audit import MCPAuditLog
from app.services.agents.mcp.mcp_client import MCPClient
from app.services.agents.mcp.mcp_registry import MCPRegistry
from app.services.agents.mcp.mcp_server import MCPServer

router = APIRouter(tags=["agent-mcp"])


class RegisterMCPServerRequest(BaseModel):
    tenant_id: str
    name: str
    transport: str = "streamable_http"
    endpoint: str
    trust_level: str = "untrusted"


class ApproveMCPToolRequest(BaseModel):
    tool_name: str


class MCPCallRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = {}


admin_router = APIRouter(prefix="/admin/agents/mcp", tags=["agent-mcp-admin"])
server_router = APIRouter(prefix="/mcp", tags=["mcp-server"])


@admin_router.get("/servers")
def list_servers(settings: Settings = Depends(get_settings), _: dict = Depends(require_admin)):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    return [server.__dict__ for server in MCPRegistry().list()]


@admin_router.post("/servers")
def register_server(req: RegisterMCPServerRequest, settings: Settings = Depends(get_settings), _: dict = Depends(require_admin)):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    server = MCPRegistry().register(req.tenant_id, req.name, req.transport, req.endpoint, req.trust_level)
    return server.__dict__


@admin_router.post("/servers/{server_id}/discover")
def discover_server(server_id: str, settings: Settings = Depends(get_settings), _: dict = Depends(require_admin)):
    try:
        return MCPClient().discover(server_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.post("/servers/{server_id}/approve-tool")
def approve_tool(server_id: str, req: ApproveMCPToolRequest, settings: Settings = Depends(get_settings), _: dict = Depends(require_admin)):
    try:
        return MCPClient().approve_tool(server_id, req.tool_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.get("/tools")
def list_tools(settings: Settings = Depends(get_settings), _: dict = Depends(require_admin)):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    tools = []
    for server in MCPRegistry().list():
        for tool in server.discovered_tools:
            tool_payload = dict(tool)
            tool_payload["server_id"] = server.id
            tool_payload["approved"] = tool["name"] in server.approved_tools
            tools.append(tool_payload)
    return tools


@admin_router.get("/audit")
def list_audit(settings: Settings = Depends(get_settings), _: dict = Depends(require_admin)):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    return MCPAuditLog.events


@server_router.get("")
def mcp_root(settings: Settings = Depends(get_settings)):
    if not settings.agent_mcp_enabled or not settings.agent_mcp_server_enabled:
        raise HTTPException(status_code=404, detail="MCP server is disabled")
    return {"protocol": "mcp", "status": "ready"}


@server_router.get("/tools")
def mcp_tools(settings: Settings = Depends(get_settings)):
    return MCPServer().list_tools()


@server_router.get("/resources")
def mcp_resources(settings: Settings = Depends(get_settings)):
    return MCPServer().list_resources()


@server_router.get("/prompts")
def mcp_prompts(settings: Settings = Depends(get_settings)):
    return MCPServer().list_prompts()


@server_router.post("/call")
def mcp_call(req: MCPCallRequest, settings: Settings = Depends(get_settings)):
    try:
        return MCPServer().call(req.tool_name, req.arguments)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
