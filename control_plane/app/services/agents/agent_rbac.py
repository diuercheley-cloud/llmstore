"""
Owner: agent-platform
Status: beta
"""
import uuid
import logging
from typing import Any, Dict, List, Optional, Iterable
from fastapi import HTTPException, Request, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentRBACEvent
from app.services.admin_rbac import AuthenticatedAdmin, record_admin_audit_event
from app.core.time import utc_now

logger = logging.getLogger(__name__)

# Define Agent-specific Permissions
AGENT_PERMISSIONS = {
    "agents:read": "Read agent definitions and runs",
    "agents:write": "Create and update agent definitions",
    "agents:execute": "Execute agent runs",
    "agents:approve": "Approve agent promotions",
    "agent_tools:read": "Read tool definitions",
    "agent_tools:write": "Manage tool definitions",
    "agent_tools:execute": "Execute tool calls",
    "agent_memory:read": "Read agent memory items",
    "agent_memory:write": "Write to agent memory",
    "agent_memory:delete": "Delete agent memory items",
    "agent_evals:read": "Read agent evaluations",
    "agent_evals:write": "Run agent evaluations",
    "agent_policies:read": "Read environment and tool policies",
    "agent_policies:write": "Manage environment and tool policies",
    "agent_incidents:read": "Read agent incidents",
    "agent_incidents:write": "Manage agent incidents",
}

# Define Agent-specific Roles
AGENT_ROLES = {
    "agent_viewer": {
        "description": "Read-only access to the agentic plane",
        "permissions": ["agents:read", "agent_tools:read", "agent_memory:read", "agent_evals:read", "agent_incidents:read"],
    },
    "agent_operator": {
        "description": "Operate and execute agents",
        "permissions": ["agents:read", "agents:execute", "agent_tools:read", "agent_tools:execute", "agent_incidents:read", "agent_incidents:write"],
    },
    "agent_developer": {
        "description": "Develop and test agents and tools",
        "permissions": ["agents:read", "agents:write", "agents:execute", "agent_tools:read", "agent_tools:write", "agent_tools:execute", "agent_evals:read", "agent_evals:write"],
    },
    "agent_reviewer": {
        "description": "Review and approve agent promotions",
        "permissions": ["agents:read", "agents:approve", "agent_evals:read"],
    },
    "agent_security_admin": {
        "description": "Manage security policies and sensitive tool classes",
        "permissions": ["agent_policies:read", "agent_policies:write", "agents:read", "agent_tools:read", "agent_tools:write"],
    },
    "agent_tool_admin": {
        "description": "Manage tool registry and execution sandboxes",
        "permissions": ["agent_tools:read", "agent_tools:write", "agent_tools:execute"],
    },
    "agent_memory_admin": {
        "description": "Manage agent memory and data retention",
        "permissions": ["agent_memory:read", "agent_memory:write", "agent_memory:delete"],
    },
    "agent_approval_reviewer": {
        "description": "Review human-in-the-loop approval requests",
        "permissions": ["agents:read", "agents:approve"],
    },
    "agent_marketplace_admin": {
        "description": "Manage agent bundles in the marketplace",
        "permissions": ["agents:read", "agents:write"],
    }
}

async def check_agent_permission(
    db: AsyncSession,
    admin: AuthenticatedAdmin,
    permission: str,
    resource_id: Optional[str] = None,
    request: Optional[Request] = None
) -> bool:
    if admin.has_permission("superadmin:all") or admin.has_permission(permission):
        return True

    # Record denial in AgentRBACEvent
    event = AgentRBACEvent(
        admin_user_id=admin.user.id,
        event_type="permission.denied",
        status="denied",
        permission_code=permission,
        resource_id=resource_id,
        actor_identifier=admin.user.username,
        metadata_json={
            "required_permission": permission,
            "granted_permissions": sorted(admin.permission_codes),
            "request_path": request.url.path if request else None,
            "request_method": request.method if request else None
        },
        created_at=utc_now()
    )
    db.add(event)
    await db.commit()

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "forbidden", "required_permission": permission}
    )

async def require_agent_permission(permission: str):
    async def decorator(
        request: Request,
        db: AsyncSession,
        admin: AuthenticatedAdmin # This is usually from Depends(require_admin)
    ):
        await check_agent_permission(db, admin, permission, request=request)
        return admin
    return decorator
