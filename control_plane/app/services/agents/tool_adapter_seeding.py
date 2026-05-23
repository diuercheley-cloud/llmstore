# Owner: agent-platform
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentTool
from app.services.agents.tool_adapter_registry import adapter_registry
from app.services.agents.tool_registry import create_tool, get_tool_by_name, update_tool

logger = logging.getLogger(__name__)

async def seed_tool_adapters(db: AsyncSession) -> None:
    """
    Syncs the ToolRegistry (database) with the ToolAdapterRegistry (code).
    Ensures that for every adapter registered in code, a corresponding tool exists in the DB.
    """
    adapters = adapter_registry.list_adapters()
    for adapter in adapters:
        existing = await get_tool_by_name(db, adapter.name)
        tool_data = adapter.to_registry_dict()
        
        # Add required defaults for database model
        if "category" not in tool_data:
            # Map side effect to category if category not explicitly provided by adapter
            category_map = {
                "none": "filesystem_safe",
                "read": "retrieval",
                "write": "support",
                "destructive": "admin_operation",
                "external": "external_api"
            }
            tool_data["category"] = category_map.get(adapter.side_effect_level, "filesystem_safe")
        
        if "description" not in tool_data:
            tool_data["description"] = f"Real tool adapter for {adapter.name}"
            
        if "timeout_seconds" not in tool_data:
            tool_data["timeout_seconds"] = 30

        try:
            if not existing:
                logger.info(f"Seeding new tool from adapter: {adapter.name}")
                await create_tool(db, tool_data)
            else:
                # Update if version or schemas changed
                if existing.version != adapter.version or \
                   existing.input_schema_json != adapter.input_schema or \
                   existing.output_schema_json != adapter.output_schema:
                    logger.info(f"Updating tool from adapter: {adapter.name} (v{existing.version} -> v{adapter.version})")
                    await update_tool(db, existing.id, tool_data)
        except Exception as e:
            logger.error(f"Failed to seed tool adapter {adapter.name}: {e}")

    await db.commit()
