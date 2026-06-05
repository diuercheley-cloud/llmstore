import uuid
from typing import List, Optional

from app.api.deps import get_db_session
from app.services.agents.protocols.service import ProtocolService
from app.services.agents.protocols.base import ProtocolType
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/protocols", tags=["admin-agent-protocols"])


@router.get("/mcp/servers")
async def list_mcp_servers(
    tenant_id: str = "default",
    session: AsyncSession = Depends(get_db_session)
):
    service = ProtocolService(session)
    return await service.list_mcp_servers(tenant_id)


@router.post("/mcp/servers/{server_id}/approve-tool")
async def approve_mcp_tool(
    server_id: uuid.UUID,
    tool_name: str = Query(...),
    session: AsyncSession = Depends(get_db_session)
):
    service = ProtocolService(session)
    await service.approve_mcp_tool(server_id, tool_name)
    return {"status": "success"}


@router.get("/a2a/peers")
async def list_a2a_peers(
    tenant_id: str = "default",
    session: AsyncSession = Depends(get_db_session)
):
    service = ProtocolService(session)
    return await service.list_a2a_peers(tenant_id)


@router.post("/a2a/handshake/dry-run")
async def a2a_handshake_dry_run(
    peer_url: str = Query(...),
    session: AsyncSession = Depends(get_db_session)
):
    service = ProtocolService(session)
    return await service.dry_run_handshake(peer_url)


@router.get("/trust/explain")
async def explain_trust_decision(
    protocol: ProtocolType,
    entity_id: uuid.UUID,
    action: str = "access",
    session: AsyncSession = Depends(get_db_session)
):
    service = ProtocolService(session)
    return await service.evaluate_trust(protocol, entity_id, action)
