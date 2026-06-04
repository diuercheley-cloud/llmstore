# Owner: agent-platform
import logging
import uuid

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.agents import AgentRun
from app.services.agents import agent_runtime
from app.services.agents.agent_cancellation import AgentCancellationService
from app.services.agents.streaming.stream_auth import StreamAuthService
from app.services.agents.streaming.websocket_manager import ws_manager
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("agents_ws")
router = APIRouter(tags=["agents-ws"])

@router.websocket("/v1/agents/runs/{run_id}/stream")
async def ws_agent_run_stream(
    websocket: WebSocket,
    run_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    # Verify feature flag
    settings = get_settings()
    if not settings.agent_websocket_streaming_enabled:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="WebSocket streaming is disabled")
        return

    # Try validating UUID format
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid run ID format")
        return

    # Authenticate client connection
    try:
        client = await StreamAuthService.authenticate_websocket(websocket, db)
    except Exception:
        # Connection closed inside auth service
        return

    # Validate that run exists and belongs to client tenant
    from sqlalchemy import select
    stmt = select(AgentRun).where(AgentRun.id == run_uuid)
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()

    if not run or run.tenant_id != str(client.id):
        logger.warning(f"Tenant isolation mismatch for run {run_id}. Client: {client.id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Run not found or tenant mismatch")
        return

    # Accept connection and register with ws_manager
    await websocket.accept()
    conn = ws_manager.connect(run_id, websocket)

    try:
        while True:
            # Handle incoming WebSocket commands from client (cancel, pause, resume)
            data = await websocket.receive_json()
            command = data.get("command")
            db.expire_all()
            if command == "cancel":
                success = await AgentCancellationService.cancel_run(db, run_uuid)
                await websocket.send_json({"status": "command_processed", "command": "cancel", "success": success})
            elif command == "pause":
                try:
                    await agent_runtime.pause_run(db, run_uuid)
                    await websocket.send_json({"status": "command_processed", "command": "pause", "success": True})
                except Exception as e:
                    await websocket.send_json({"status": "command_processed", "command": "pause", "success": False, "error": str(e)})
            elif command == "resume":
                try:
                    await agent_runtime.resume_run(db, run_uuid)
                    await websocket.send_json({"status": "command_processed", "command": "resume", "success": True})
                except Exception as e:
                    await websocket.send_json({"status": "command_processed", "command": "resume", "success": False, "error": str(e)})
            else:
                await websocket.send_json({"status": "error", "message": f"Unknown command: {command}"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from run stream {run_id}")
    except Exception as e:
        logger.error(f"WebSocket session error for run {run_id}: {e}")
    finally:
        await ws_manager.disconnect(run_id, conn)
