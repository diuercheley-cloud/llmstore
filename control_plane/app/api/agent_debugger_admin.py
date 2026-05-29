# Owner: agent-platform
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.agents.debugger.time_travel_debugger import TimeTravelDebugger

router = APIRouter(prefix="/admin/agents", tags=["Agent Time-Travel Debugger"])

@router.get("/runs/{run_id}/snapshots")
async def list_run_snapshots(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    debugger = TimeTravelDebugger(db)
    return await debugger.get_run_snapshots(run_id)

@router.post("/runs/{run_id}/debug/replay-from-step")
async def replay_from_step(
    run_id: uuid.UUID,
    step_number: int,
    db: AsyncSession = Depends(get_db)
):
    debugger = TimeTravelDebugger(db)
    try:
        return await debugger.start_replay(run_id, step_number)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/debug/{debug_id}/state-edit")
async def edit_debug_state(
    debug_id: uuid.UUID,
    edit_data: Dict[str, Any],
    editor_id: str,
    db: AsyncSession = Depends(get_db)
):
    debugger = TimeTravelDebugger(db)
    try:
        return await debugger.apply_edit(
            debug_id, 
            edit_data["field"], 
            edit_data["value"], 
            editor_id
        )
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/debug/{debug_id}/diff")
async def get_debug_diff(
    debug_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    debugger = TimeTravelDebugger(db)
    try:
        return await debugger.get_comparison(debug_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
