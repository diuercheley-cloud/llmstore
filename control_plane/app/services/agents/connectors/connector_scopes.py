# Owner: agent-platform
import logging
from typing import List

from app.models.connector_auth import ConnectorScopePolicy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class ConnectorScopeManager:
    """
    Enforces scope policies for SaaS connectors.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_scopes(self, tenant_id: str, connector_name: str, action: str, provided_scopes: List[str]) -> bool:
        stmt = select(ConnectorScopePolicy).where(
            ConnectorScopePolicy.tenant_id == tenant_id,
            ConnectorScopePolicy.connector_name == connector_name,
            ConnectorScopePolicy.action == action
        )
        res = await self.db.execute(stmt)
        policy = res.scalar_one_or_none()
        
        if not policy:
            # Default to requiring no special scopes if no policy defined
            return True
            
        required = policy.required_scopes
        return all(s in provided_scopes for s in required)

    async def create_policy(self, tenant_id: str, connector_name: str, action: str, required_scopes: List[str]):
        policy = ConnectorScopePolicy(
            tenant_id=tenant_id,
            connector_name=connector_name,
            action=action,
            required_scopes=required_scopes
        )
        self.db.add(policy)
        await self.db.flush()
        return policy
