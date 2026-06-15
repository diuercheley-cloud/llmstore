# Owner: agent-platform
import uuid
from datetime import datetime
from typing import Any

from app.api.deps import require_admin
from app.core.config import Settings, get_settings
from app.services.agents.mcp.mcp_audit import MCPAuditLog
from app.services.agents.mcp.mcp_client import MCPClient
from app.services.agents.mcp.mcp_oauth import (
    MCPOAuthAuditLog,
    create_mcp_delegated_grant,
    create_mcp_oauth_client,
    delete_mcp_delegated_grant,
)
from app.services.agents.mcp.mcp_registry import MCPRegistry
from app.services.agents.mcp.mcp_server import MCPServer
from app.services.agents.mcp.mcp_token_exchange import exchange_token
from app.services.runtime_dependencies import get_db_session
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

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
async def list_servers(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    return [server.__dict__ for server in await MCPRegistry().list_persistent(db)]


@admin_router.post("/servers")
async def register_server(
    req: RegisterMCPServerRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    server = await MCPRegistry().register_persistent(
        db,
        req.tenant_id,
        req.name,
        req.transport,
        req.endpoint,
        req.trust_level,
    )
    return server.__dict__


@admin_router.post("/servers/{server_id}/discover")
async def discover_server(
    server_id: str,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    try:
        return await MCPClient(db).discover(server_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.post("/servers/{server_id}/approve-tool")
async def approve_tool(
    server_id: str,
    req: ApproveMCPToolRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    try:
        return await MCPClient(db).approve_tool(server_id, req.tool_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.post("/tools/{tool_name}/call")
async def call_tool(
    tool_name: str,
    req: MCPCallRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    # server_id must be supplied in the request body
    server_id = req.arguments.pop("__server_id", None)
    if not server_id:
        raise HTTPException(status_code=422, detail="__server_id must be provided in arguments")
    try:
        return await MCPClient(db).call_tool(server_id, tool_name, req.arguments)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@admin_router.get("/tools")
async def list_tools(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    tools = []
    for server in await MCPRegistry().list_persistent(db):
        for tool in server.discovered_tools:
            tool_payload = dict(tool)
            tool_payload["server_id"] = server.id
            tool_payload["approved"] = tool["name"] in server.approved_tools
            tools.append(tool_payload)
    return tools


@admin_router.get("/audit")
def list_audit(
    event_type: str | None = None,
    server_id: str | None = None,
    limit: int = 200,
    settings: Settings = Depends(get_settings),
    _: dict = Depends(require_admin),
):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    return MCPAuditLog.list_events(event_type=event_type, server_id=server_id, limit=limit)


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


class CreateMCPOAuthClientRequest(BaseModel):
    tenant_id: str
    name: str
    client_id: str
    client_secret: str
    auth_url: str | None = None
    token_url: str | None = None
    default_scopes: list[str] = []


class CreateMCPDelegatedGrantRequest(BaseModel):
    tenant_id: str
    user_id: str
    agent_id: uuid.UUID | None = None
    mcp_server: str
    access_token: str
    refresh_token: str | None = None
    scopes: list[str] = []
    expires_at: datetime | None = None


class TokenExchangeApiRequest(BaseModel):
    tenant_id: str
    subject_token: str
    subject_token_type: str = "urn:ietf:params:oauth:token-type:access_token"
    mcp_server: str
    requested_scopes: list[str] = []


def serialize_client(client) -> dict:
    return {
        "id": str(client.id),
        "tenant_id": client.tenant_id,
        "name": client.name,
        "client_id": client.client_id,
        "client_secret_hash": "[REDACTED]",
        "auth_url": client.auth_url,
        "token_url": client.token_url,
        "default_scopes": client.default_scopes,
        "created_at": client.created_at.isoformat() if client.created_at else None,
        "updated_at": client.updated_at.isoformat() if client.updated_at else None,
    }


def serialize_grant(grant) -> dict:
    return {
        "id": str(grant.id),
        "tenant_id": grant.tenant_id,
        "user_id": grant.user_id,
        "agent_id": str(grant.agent_id) if grant.agent_id else None,
        "mcp_server": grant.mcp_server,
        "access_token": "[REDACTED]",
        "refresh_token": "[REDACTED]" if grant.refresh_token else None,
        "scopes": grant.scopes,
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
        "is_revoked": grant.is_revoked,
        "created_at": grant.created_at.isoformat() if grant.created_at else None,
        "updated_at": grant.updated_at.isoformat() if grant.updated_at else None,
    }


@admin_router.post("/oauth/clients")
async def create_oauth_client_endpoint(
    req: CreateMCPOAuthClientRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    client = await create_mcp_oauth_client(
        db,
        req.tenant_id,
        req.name,
        req.client_id,
        req.client_secret,
        req.auth_url,
        req.token_url,
        req.default_scopes,
    )
    return serialize_client(client)


@admin_router.post("/oauth/grants")
async def create_delegated_grant_endpoint(
    req: CreateMCPDelegatedGrantRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    grant = await create_mcp_delegated_grant(
        db,
        req.tenant_id,
        req.user_id,
        req.agent_id,
        req.mcp_server,
        req.access_token,
        req.refresh_token,
        req.scopes,
        req.expires_at,
    )
    return serialize_grant(grant)


@admin_router.delete("/oauth/grants/{grant_id}")
async def delete_delegated_grant_endpoint(
    grant_id: uuid.UUID,
    tenant_id: str,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    success = await delete_mcp_delegated_grant(db, grant_id, tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Grant not found or tenant mismatch")
    return {"id": str(grant_id), "deleted": True}


@admin_router.post("/oauth/token-exchange")
async def token_exchange_endpoint(
    req: TokenExchangeApiRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    return await exchange_token(
        db,
        req.tenant_id,
        req.subject_token,
        req.subject_token_type,
        req.mcp_server,
        req.requested_scopes,
    )


@admin_router.get("/oauth/audit")
def list_oauth_audit(
    settings: Settings = Depends(get_settings),
    _: dict = Depends(require_admin),
):
    if not settings.agent_mcp_enabled:
        raise HTTPException(status_code=400, detail="MCP is not enabled")
    return MCPOAuthAuditLog.events
