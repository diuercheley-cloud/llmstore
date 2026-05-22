import os
import yaml
import uuid
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentRegistryEntry, AgentVersion, AgentLifecycleEvent
from app.core.time import utc_now

logger = logging.getLogger(__name__)

def load_registry_config() -> Dict[str, Any]:
    """Loads configuration parameters from config/agent-registry.yaml."""
    config_path = os.path.join(os.getcwd(), "config", "agent-registry.yaml")
    if not os.path.exists(config_path):
        this_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.abspath(os.path.join(this_dir, "..", "..", "..", "..", "config", "agent-registry.yaml"))

    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                if config and isinstance(config, dict):
                    return config
        except Exception as e:
            logger.warning(f"Failed to load agent-registry config from {config_path}: {e}")
            
    return {
        "risk_levels": ["low", "medium", "high", "critical"],
        "destructive_tools": ["write", "delete", "destroy", "remove", "update"]
    }

def bump_version(version_str: str) -> str:
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

async def get_registry_entry(db: AsyncSession, entry_id: uuid.UUID) -> Optional[AgentRegistryEntry]:
    """Fetches a single Agent Registry entry by database ID."""
    result = await db.execute(select(AgentRegistryEntry).where(AgentRegistryEntry.id == entry_id))
    return result.scalars().first()

async def get_registry_entry_by_agent_id(db: AsyncSession, agent_id: uuid.UUID) -> Optional[AgentRegistryEntry]:
    """Fetches a single Agent Registry entry by public agent UUID."""
    result = await db.execute(select(AgentRegistryEntry).where(AgentRegistryEntry.agent_id == agent_id))
    return result.scalars().first()

async def get_registry_entries(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    owner: Optional[str] = None
) -> List[AgentRegistryEntry]:
    """Retrieves list of registry entries filtered by status and owner."""
    query = select(AgentRegistryEntry)
    if status:
        query = query.where(AgentRegistryEntry.status == status)
    if owner:
        query = query.where(AgentRegistryEntry.owner == owner)
    
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())

async def get_agent_versions(db: AsyncSession, entry_id: uuid.UUID) -> List[AgentVersion]:
    """Retrieves all versions registered for a given agent entry."""
    result = await db.execute(
        select(AgentVersion)
        .where(AgentVersion.agent_registry_id == entry_id)
        .order_by(AgentVersion.created_at.desc())
    )
    return list(result.scalars().all())

async def create_registry_entry(db: AsyncSession, data: Dict[str, Any], performed_by: str = "system") -> AgentRegistryEntry:
    """Creates a new agent catalog entry in draft status and registers its initial version."""
    config = load_registry_config()
    
    # Validate risk level
    risk_level = data.get("risk_level", "low")
    if risk_level not in config.get("risk_levels", []):
        raise ValueError(f"Invalid risk_level: '{risk_level}'. Must be one of {config.get('risk_levels')}")

    # Check for destructive tools to default human approval
    allowed_tools = data.get("allowed_tools") or []
    destructive_tools = config.get("destructive_tools", [])
    has_destructive = False
    for tool in allowed_tools:
        if str(tool).lower() in [t.lower() for t in destructive_tools]:
            has_destructive = True
            break
            
    if has_destructive:
        data["human_approval_required"] = True

    # Ensure status starts as draft
    data["status"] = "draft"
    
    entry = AgentRegistryEntry(**data)
    db.add(entry)
    await db.flush()  # Populates entry.id

    # Create the initial version
    initial_version = AgentVersion(
        agent_registry_id=entry.id,
        semantic_version=entry.semantic_version,
        instructions=entry.instructions,
        allowed_tools=entry.allowed_tools,
        allowed_models=entry.allowed_models
    )
    db.add(initial_version)

    # Log lifecycle event
    event = AgentLifecycleEvent(
        agent_registry_id=entry.id,
        event_type="create_draft",
        from_status="none",
        to_status="draft",
        performed_by=performed_by,
        notes="Agent registry entry initialized as draft"
    )
    db.add(event)
    
    await db.commit()
    await db.refresh(entry)
    return entry

async def update_registry_entry(
    db: AsyncSession,
    entry_id: uuid.UUID,
    update_data: Dict[str, Any],
    performed_by: str = "system"
) -> AgentRegistryEntry:
    """Updates registry entry metadata and creates a new version record if instructions changed."""
    entry = await get_registry_entry(db, entry_id)
    if not entry:
        raise ValueError(f"Agent Registry Entry not found: {entry_id}")

    config = load_registry_config()

    # Enforce experimental to supported gate
    if "supported_surface_status" in update_data:
        if update_data["supported_surface_status"] == "supported" and entry.supported_surface_status == "experimental":
            raise ValueError("Experimental agents cannot be promoted to supported.")

    # Validate risk level if updated
    if "risk_level" in update_data:
        risk_level = update_data["risk_level"]
        if risk_level not in config.get("risk_levels", []):
            raise ValueError(f"Invalid risk_level: '{risk_level}'. Must be one of {config.get('risk_levels')}")

    # Re-evaluate destructive tools if allowed_tools is modified
    if "allowed_tools" in update_data:
        allowed_tools = update_data["allowed_tools"] or []
        destructive_tools = config.get("destructive_tools", [])
        has_destructive = False
        for tool in allowed_tools:
            if str(tool).lower() in [t.lower() for t in destructive_tools]:
                has_destructive = True
                break
        if has_destructive:
            update_data["human_approval_required"] = True

    # Detect instruction changes
    old_instructions = entry.instructions
    new_instructions = update_data.get("instructions", old_instructions)
    instructions_changed = ("instructions" in update_data and new_instructions != old_instructions)

    # Resolve semantic version bumping
    old_version = entry.semantic_version
    new_version = update_data.get("semantic_version", old_version)

    if instructions_changed and new_version == old_version:
        new_version = bump_version(old_version)
        update_data["semantic_version"] = new_version

    # Apply updates
    for key, val in update_data.items():
        setattr(entry, key, val)

    # Save new version if instructions changed
    if instructions_changed:
        new_version_record = AgentVersion(
            agent_registry_id=entry.id,
            semantic_version=new_version,
            instructions=new_instructions,
            allowed_tools=entry.allowed_tools,
            allowed_models=entry.allowed_models
        )
        db.add(new_version_record)
        
        # Log version bump event
        event = AgentLifecycleEvent(
            agent_registry_id=entry.id,
            event_type="version_bump",
            from_status=entry.status,
            to_status=entry.status,
            performed_by=performed_by,
            notes=f"Instructions changed: version bumped from {old_version} to {new_version}"
        )
        db.add(event)

    await db.commit()
    await db.refresh(entry)
    return entry
