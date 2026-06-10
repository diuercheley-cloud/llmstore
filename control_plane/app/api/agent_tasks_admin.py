# Owner: agent-platform
import uuid
from typing import Any, Dict, List

from app.api.deps import get_db_session, require_admin
from app.models.agents.agents import AgentTask
from app.services.agents.agent_planner import AgentPlanner
from app.services.agents.task_engine import TaskEngine
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agent-tasks", tags=["agent-tasks"])

@router.post("/plans")
async def create_plan(
    agent_run_id: uuid.UUID = Body(...),
    goal: str = Body(...),
    tasks: List[dict] = Body(...),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    planner = AgentPlanner(db)
    plan = await planner.create_plan(agent_run_id, goal, tasks)
    return {"id": str(plan.id), "status": plan.status}

@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    planner = AgentPlanner(db)
    plan = await planner.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Fetch tasks
    stmt = select(AgentTask).where(AgentTask.plan_id == plan_id)
    res = await db.execute(stmt)
    tasks = res.scalars().all()
    
    return {
        "id": str(plan.id),
        "status": plan.status,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "attempt_count": t.attempt_count
            }
            for t in tasks
        ]
    }

@router.post("/plans/{plan_id}/execute")
async def execute_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    engine = TaskEngine(db)
    # This might be long running, should probably be async/background
    # For now, we call it and return
    import asyncio
    asyncio.create_task(engine.execute_plan(plan_id))
    return {"status": "execution_started"}

@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    engine = TaskEngine(db)
    await engine.retry_task(task_id)
    return {"status": "pending"}

@router.post("/tasks/{task_id}/skip")
async def skip_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    engine = TaskEngine(db)
    await engine.skip_task(task_id)
    return {"status": "skipped"}

@router.post("/tasks/{task_id}/compensate")
async def compensate_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    from app.services.agents.compensation import CompensationService
    service = CompensationService(db)
    await service.trigger_compensation(task_id)
    return {"status": "compensation_triggered"}
