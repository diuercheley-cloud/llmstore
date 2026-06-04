# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.models.agents import (
    AgentTool,
    AgentToolPermission,
    AgentToolSafetyReview,
    AgentToolVersion,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {
    "retrieval",
    "filesystem_safe",
    "database_read",
    "database_write",
    "admin_operation",
    "deployment",
    "billing",
    "support",
    "compliance",
    "external_api",
    "shell_command"
}

VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}
VALID_SIDE_EFFECTS = {"none", "read", "write", "destructive", "external", "external_read"}


def bump_patch_version(version_str: str) -> str:
    """Safely increments the patch number of a semantic version string."""
    try:
        parts = version_str.split('.')
        if len(parts) >= 3:
            patch = int(parts[2])
            return f"{parts[0]}.{parts[1]}.{patch + 1}"
        elif len(parts) == 2:
            minor = int(parts[1])
            return f"{parts[0]}.{minor + 1}.0"
        else:
            val = int(parts[0])
            return f"{val + 1}.0.0"
    except Exception:
        return version_str + ".1"


async def get_tool(db: AsyncSession, tool_id: uuid.UUID) -> Optional[AgentTool]:
    """Fetches a single AgentTool by database ID."""
    result = await db.execute(select(AgentTool).where(AgentTool.id == tool_id))
    return result.scalars().first()


async def get_tool_by_name(db: AsyncSession, name: str) -> Optional[AgentTool]:
    """Fetches a single AgentTool by its name."""
    result = await db.execute(select(AgentTool).where(AgentTool.name == name))
    return result.scalars().first()


async def list_tools(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    category: Optional[str] = None,
    enabled: Optional[bool] = None
) -> List[AgentTool]:
    """Lists registered tools with optional filters."""
    query = select(AgentTool)
    if category:
        query = query.where(AgentTool.category == category)
    if enabled is not None:
        query = query.where(AgentTool.enabled == enabled)
    
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_tool_versions(db: AsyncSession, tool_id: uuid.UUID) -> List[AgentToolVersion]:
    """Retrieves all version snapshots registered for a given tool."""
    result = await db.execute(
        select(AgentToolVersion)
        .where(AgentToolVersion.agent_tool_id == tool_id)
        .order_by(AgentToolVersion.created_at.desc())
    )
    return list(result.scalars().all())


def validate_tool_data(data: Dict[str, Any]) -> None:
    """Enforces governance and structural constraints on tool data."""
    # 1. Tool MUST have input and output schemas
    input_schema = data.get("input_schema_json")
    output_schema = data.get("output_schema_json")
    if not input_schema or not isinstance(input_schema, dict):
        raise ValueError("Tool must specify a valid input_schema_json.")
    if not output_schema or not isinstance(output_schema, dict):
        raise ValueError("Tool must specify a valid output_schema_json.")

    # Validate category
    category = data.get("category")
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Must be one of {VALID_CATEGORIES}")

    # 1.1 Risk level is mandatory
    risk_level = data.get("risk_level")
    if risk_level not in VALID_RISK_LEVELS:
        raise ValueError(f"Tool must define a valid risk_level. One of {VALID_RISK_LEVELS}")

    # Validate side effect level
    side_effect_level = data.get("side_effect_level", "none")
    if side_effect_level not in VALID_SIDE_EFFECTS:
        raise ValueError(f"Invalid side_effect_level '{side_effect_level}'. Must be one of {VALID_SIDE_EFFECTS}")

    # 3. Tool external_api or side_effect external/external_read must declare data_boundary
    if category == "external_api" or side_effect_level in ("external", "external_read"):
        data_boundary = data.get("data_boundary")
        if not data_boundary or not str(data_boundary).strip():
            raise ValueError("External tools must declare a non-empty 'data_boundary'.")

    # 3.1 Write/destructive exige approval policy
    if side_effect_level in ("write", "destructive"):
        if not data.get("approval_policy"):
             raise ValueError(f"Tools with side_effect '{side_effect_level}' must define an 'approval_policy'.")

    # 7. Timeout is mandatory
    timeout = data.get("timeout_seconds")
    if timeout is None or not isinstance(timeout, int) or timeout <= 0:
        raise ValueError("Tool must define a positive integer timeout_seconds.")


async def create_tool(db: AsyncSession, data: Dict[str, Any]) -> AgentTool:
    """Registers a new tool in the catalog, enforces defaults, and creates version snapshot."""
    
    # Defaults for new fields if missing
    if "scope" not in data: data["scope"] = "tenant"
    if "max_cost_brl" not in data: data["max_cost_brl"] = 0.5  # Conservative default
    if "max_calls_per_run" not in data: data["max_calls_per_run"] = 5

    # Enforce default rules
    validate_tool_data(data)

    category = data.get("category")
    side_effect = data.get("side_effect_level", "none")

    # 2. Tool write/destructive exige approval por padrão
    if data.get("requires_approval") is None:
        data["requires_approval"] = side_effect in ("write", "destructive")

    # 4. Shell/HTTP/DB tools are disabled by default
    if data.get("enabled") is None:
        disabled_by_default_categories = {"shell_command", "external_api", "database_write"}
        data["enabled"] = category not in disabled_by_default_categories

    # Check uniqueness of name
    existing = await get_tool_by_name(db, data["name"])
    if existing:
        raise ValueError(f"AgentTool with name '{data['name']}' already exists.")

    tool = AgentTool(**data)
    db.add(tool)
    await db.flush()  # Populates tool.id

    # Add initial version snapshot
    version_snapshot = AgentToolVersion(
        agent_tool_id=tool.id,
        version=tool.version,
        description=tool.description,
        input_schema_json=tool.input_schema_json,
        output_schema_json=tool.output_schema_json,
        risk_level=tool.risk_level,
        side_effect_level=tool.side_effect_level,
        timeout_seconds=tool.timeout_seconds,
        retry_policy=tool.retry_policy,
        scope=tool.scope,
        max_cost_brl=tool.max_cost_brl,
        max_calls_per_run=tool.max_calls_per_run,
        approval_policy=tool.approval_policy
    )
    db.add(version_snapshot)
    await db.commit()
    await db.refresh(tool)
    return tool


async def update_tool(db: AsyncSession, tool_id: uuid.UUID, update_data: Dict[str, Any]) -> AgentTool:
    """Updates metadata and creates a new version history snapshot if definition properties change."""
    tool = await get_tool(db, tool_id)
    if not tool:
        raise ValueError(f"AgentTool not found: {tool_id}")

    # Gather data after update to validate it as a whole
    merged = {
        "name": update_data.get("name", tool.name),
        "category": update_data.get("category", tool.category),
        "input_schema_json": update_data.get("input_schema_json", tool.input_schema_json),
        "output_schema_json": update_data.get("output_schema_json", tool.output_schema_json),
        "risk_level": update_data.get("risk_level", tool.risk_level),
        "side_effect_level": update_data.get("side_effect_level", tool.side_effect_level),
        "timeout_seconds": update_data.get("timeout_seconds", tool.timeout_seconds),
        "data_boundary": update_data.get("data_boundary", tool.data_boundary),
        "version": update_data.get("version", tool.version),
    }
    validate_tool_data(merged)

    # Detect version-impacting changes
    has_changes = (
        ("description" in update_data and update_data["description"] != tool.description) or
        ("input_schema_json" in update_data and update_data["input_schema_json"] != tool.input_schema_json) or
        ("output_schema_json" in update_data and update_data["output_schema_json"] != tool.output_schema_json) or
        ("risk_level" in update_data and update_data["risk_level"] != tool.risk_level) or
        ("side_effect_level" in update_data and update_data["side_effect_level"] != tool.side_effect_level) or
        ("timeout_seconds" in update_data and update_data["timeout_seconds"] != tool.timeout_seconds) or
        ("retry_policy" in update_data and update_data["retry_policy"] != tool.retry_policy)
    )

    old_version = tool.version
    new_version = update_data.get("version", old_version)

    if has_changes and new_version == old_version:
        new_version = bump_patch_version(old_version)
        update_data["version"] = new_version

    # Enforce category write/destructive requires_approval on changes
    if "side_effect_level" in update_data and update_data["side_effect_level"] in ("write", "destructive"):
        update_data["requires_approval"] = True

    # Enforce category shell_command default disabled when category changes to it
    if "category" in update_data and update_data["category"] == "shell_command":
        # Keep current enablement unless explicitly set
        if "enabled" not in update_data:
            update_data["enabled"] = False

    for key, val in update_data.items():
        setattr(tool, key, val)

    if has_changes:
        version_snapshot = AgentToolVersion(
            agent_tool_id=tool.id,
            version=new_version,
            description=tool.description,
            input_schema_json=tool.input_schema_json,
            output_schema_json=tool.output_schema_json,
            risk_level=tool.risk_level,
            side_effect_level=tool.side_effect_level,
            timeout_seconds=tool.timeout_seconds,
            retry_policy=tool.retry_policy
        )
        db.add(version_snapshot)

    await db.commit()
    await db.refresh(tool)
    return tool


async def enable_tool(db: AsyncSession, tool_id: uuid.UUID) -> AgentTool:
    """Enables a tool in the registry."""
    tool = await get_tool(db, tool_id)
    if not tool:
        raise ValueError(f"AgentTool not found: {tool_id}")
    tool.enabled = True
    await db.commit()
    await db.refresh(tool)
    return tool


async def disable_tool(db: AsyncSession, tool_id: uuid.UUID) -> AgentTool:
    """Disables a tool in the registry."""
    tool = await get_tool(db, tool_id)
    if not tool:
        raise ValueError(f"AgentTool not found: {tool_id}")
    tool.enabled = False
    await db.commit()
    await db.refresh(tool)
    return tool


async def grant_permission(
    db: AsyncSession,
    tool_id: uuid.UUID,
    agent_id: Optional[uuid.UUID],
    tenant_id: Optional[str],
    granted_by: str
) -> AgentToolPermission:
    """Grants tool execution permission for a tenant and/or agent."""
    tool = await get_tool(db, tool_id)
    if not tool:
        raise ValueError(f"AgentTool not found: {tool_id}")

    permission = AgentToolPermission(
        agent_tool_id=tool_id,
        agent_id=agent_id,
        tenant_id=tenant_id,
        granted_by=granted_by
    )
    db.add(permission)
    await db.commit()
    return permission


async def add_safety_review(
    db: AsyncSession,
    tool_id: uuid.UUID,
    reviewer: str,
    decision: str,
    notes: Optional[str] = None
) -> AgentToolSafetyReview:
    """Registers a safety review decision for the tool. If approved, resets requires_approval."""
    tool = await get_tool(db, tool_id)
    if not tool:
        raise ValueError(f"AgentTool not found: {tool_id}")

    if decision not in ("approved", "rejected"):
        raise ValueError("Decision must be either 'approved' or 'rejected'.")

    review = AgentToolSafetyReview(
        agent_tool_id=tool_id,
        reviewer=reviewer,
        decision=decision,
        notes=notes
    )
    db.add(review)

    if decision == "approved":
        tool.requires_approval = False

    await db.commit()
    return review
