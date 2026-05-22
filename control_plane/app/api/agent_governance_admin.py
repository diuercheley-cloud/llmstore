import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import require_admin, get_db_session
from app.services.agents.agent_policy_engine import AgentPolicyEngine

router = APIRouter(prefix="/admin/agents/governance", tags=["agent-governance"])

@router.get("/policies")
async def list_global_policies(
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    # In a real scenario, these would be loaded from config/agent-policies/*.yaml
    return {
        "policies": [
            {"name": "max_steps_by_risk", "status": "active"},
            {"name": "allowed_tools_by_agent", "status": "active"},
            {"name": "no_shell_tool_by_default", "status": "active"},
            {"name": "approval_required_for_destructive_tools", "status": "active"},
            {"name": "no_production_agent_without_eval_baseline", "status": "active"},
        ]
    }

@router.post("/policies/simulate")
async def simulate_policy(
    agent_id: uuid.UUID = Body(...),
    action: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> Dict[str, Any]:
    engine = AgentPolicyEngine(db)
    return await engine.simulate_action(agent_id, action)

@router.get("/decisions")
async def list_recent_decisions(
    tenant_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(require_admin),
) -> List[Dict[str, Any]]:
    # Placeholder for recent policy engine logs
    return []
