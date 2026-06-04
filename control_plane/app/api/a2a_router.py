"""
A2A (Agent-to-Agent) Protocol API router.
Implements both client and server sides of the Google A2A spec.
"""

import logging
from typing import Any, Dict

from app.api import deps
from app.core.config import get_settings
from app.services.agents.a2a.a2a_protocol import A2AClient, A2AServer
from fastapi import APIRouter, Depends, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter()

_a2a_servers: Dict[str, A2AServer] = {}


def register_a2a_server(server: A2AServer):
    _a2a_servers[server.agent_id] = server


@router.post("/a2a/jsonrpc")
async def a2a_jsonrpc(request: Request):
    """
    A2A JSON-RPC endpoint.
    Handles: agents/discover, tasks/send, tasks/get, tasks/cancel
    """
    settings = get_settings()
    if not settings.a2a_enabled:
        raise HTTPException(status_code=501, detail="A2A protocol is disabled")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON-RPC request")

    method = body.get("method", "")
    agent_id = body.get("params", {}).get("agent_id")

    if agent_id and agent_id in _a2a_servers:
        server = _a2a_servers[agent_id]
    elif _a2a_servers:
        server = list(_a2a_servers.values())[0]
    else:
        raise HTTPException(status_code=404, detail="No A2A agent server registered")

    result = await server.handle_jsonrpc(body)
    return result


@router.get("/a2a/discover/{agent_id}")
async def a2a_discover(agent_id: str):
    """Discover an agent's capabilities via A2A."""
    settings = get_settings()
    if not settings.a2a_enabled:
        raise HTTPException(status_code=501, detail="A2A protocol is disabled")

    server = _a2a_servers.get(agent_id)
    if not server:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not registered for A2A")

    card = server.get_card()
    return {
        "agentId": card.agent_id,
        "name": card.name,
        "description": card.description,
        "version": card.version,
        "capabilities": card.capabilities,
        "skills": card.skills,
    }


@router.post("/a2a/send")
async def a2a_send_task(
    target_url: str = "",
    task_data: Dict[str, Any] = {},
):
    """Send a task to a remote agent via A2A protocol."""
    settings = get_settings()
    if not settings.a2a_enabled:
        raise HTTPException(status_code=501, detail="A2A protocol is disabled")
    if not target_url:
        raise HTTPException(status_code=400, detail="target_url is required")

    client = A2AClient()
    from app.services.agents.a2a.a2a_protocol import (
        A2AMessage,
        A2AMessageRole,
        A2APart,
        A2ATask,
        A2ATaskState,
    )

    task = A2ATask(
        id=task_data.get("id", ""),
        session_id=task_data.get("sessionId", ""),
        state=A2ATaskState.SUBMITTED,
        history=[],
        metadata=task_data.get("metadata", {}),
    )

    if "message" in task_data:
        task.history.append(A2AMessage(
            role=A2AMessageRole.USER,
            parts=[A2APart.from_text(task_data["message"])],
        ))

    result = await client.send_task(target_url, task)
    await client.close()
    return result.to_dict()


@router.post("/a2a/register-server")
async def a2a_register_server(
    agent_id: str,
    name: str,
    description: str,
    current_user=Depends(deps.get_current_admin_user),
):
    """Register an agent as an A2A server."""
    settings = get_settings()
    if not settings.a2a_enabled:
        raise HTTPException(status_code=501, detail="A2A protocol is disabled")

    server = A2AServer(agent_id=agent_id, name=name, description=description)
    register_a2a_server(server)

    return {"status": "registered", "agent_id": agent_id, "name": name}
