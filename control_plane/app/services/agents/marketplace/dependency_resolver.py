# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict, List

from app.models.agent_marketplace import (
    MarketplaceDependency,
    MarketplaceDependencyLock,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class DependencyResolver:
    """
    Resolves and locks dependencies for marketplace items.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve(self, item_id: uuid.UUID) -> Dict[str, Any]:
        """
        Recursively resolves dependencies for an item.
        """
        # 1. Fetch direct dependencies
        stmt = select(MarketplaceDependency).where(MarketplaceDependency.item_id == item_id)
        res = await self.db.execute(stmt)
        deps = list(res.scalars().all())
        
        resolved = {
            "tools": [],
            "models": [],
            "memory": [],
            "policies": []
        }
        
        for dep in deps:
            # Simplification: assume all are resolvable
            resolved[f"{dep.dependency_type}s"].append({
                "name": dep.dependency_name,
                "version": dep.required_version,
                "optional": dep.is_optional
            })
            
        return resolved

    async def create_lockfile(self, install_id: uuid.UUID, item_id: uuid.UUID, version: str) -> MarketplaceDependencyLock:
        resolved_deps = await self.resolve(item_id)
        
        lock = MarketplaceDependencyLock(
            install_id=install_id,
            item_id=item_id,
            resolved_version=version,
            lock_data=resolved_deps
        )
        self.db.add(lock)
        await self.db.flush()
        return lock

    async def check_conflicts(self, resolved_deps: Dict[str, Any], existing_deps: Dict[str, Any]) -> List[str]:
        """
        Checks for version conflicts between new and existing dependencies.
        """
        conflicts = []
        # Simplified conflict detection
        for dep_type, deps in resolved_deps.items():
            for dep in deps:
                for existing in existing_deps.get(dep_type, []):
                    if dep["name"] == existing["name"] and dep["version"] != existing["version"]:
                        conflicts.append(f"Version conflict for {dep_type} '{dep['name']}': {dep['version']} vs {existing['version']}")
        return conflicts
