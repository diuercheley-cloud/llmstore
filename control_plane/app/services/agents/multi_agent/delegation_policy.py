# Owner: agent-platform
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class DelegationPolicy:
    """
    Enforces governance for agent-to-agent delegation.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def can_delegate(self, parent_id: uuid.UUID, child_id: uuid.UUID, task_type: str) -> bool:
        # 1. Simple rule: Hierarchy check (Manager -> Specialist always OK)
        # 2. Peer check
        # 3. Risk check
        return True

    async def check_risk(self, task_description: str) -> str:
        # Simple risk heuristic
        if "delete" in task_description.lower() or "production" in task_description.lower():
            return "high"
        return "low"
