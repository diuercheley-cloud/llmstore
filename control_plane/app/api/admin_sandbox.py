from typing import List, Optional

from app.api.deps import get_db_session
from app.services.sandbox.service import SandboxService
from app.services.sandbox.base import SandboxLevel
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(prefix="/admin/sandbox", tags=["admin-sandbox"])


@router.get("/providers")
async def list_sandbox_providers(
    service: SandboxService = Depends(SandboxService)
):
    """
    Lists all configured sandbox providers and their availability.
    """
    return service.list_providers()


@router.post("/dry-run")
async def sandbox_dry_run(
    tool_name: str,
    command: List[str],
    requested_level: SandboxLevel = SandboxLevel.NONE,
    service: SandboxService = Depends(SandboxService)
):
    """
    Simulates a tool execution in the sandbox environment.
    """
    result = await service.execute_tool_safely(tool_name, command, requested_level)
    
    return {
        "tool_name": tool_name,
        "requested_level": requested_level,
        "result": result,
        "policy_applied": service._get_policy_for_tool(tool_name, requested_level)
    }


@router.get("/explain/{tool_name}")
async def explain_sandbox_requirement(
    tool_name: str,
    requested_level: SandboxLevel = SandboxLevel.NONE,
    service: SandboxService = Depends(SandboxService)
):
    """
    Explains why a specific sandbox level is required for a tool.
    """
    policy = service._get_policy_for_tool(tool_name, requested_level)
    
    explanation = "Safe tool, no special sandbox required."
    if policy.required_level != SandboxLevel.NONE and requested_level == SandboxLevel.NONE:
        explanation = f"Tool '{tool_name}' is classified as dangerous and automatically promoted to {policy.required_level.value}."
    
    return {
        "tool_name": tool_name,
        "required_level": policy.required_level,
        "explanation": explanation,
        "constraints": {
            "network": policy.allow_network,
            "filesystem": policy.allow_filesystem,
            "timeout": f"{policy.timeout_seconds}s",
            "memory": f"{policy.memory_limit_mb}MB"
        }
    }
