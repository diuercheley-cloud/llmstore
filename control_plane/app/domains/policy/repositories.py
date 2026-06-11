from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.governance.policy_engine import DeterministicPolicy
from .contracts import PolicyRepository, PolicyData

class SqlAlchemyPolicyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _map_policy(self, policy: DeterministicPolicy) -> PolicyData:
        return PolicyData(
            id=policy.id,
            client_id=str(policy.client_id),
            name=policy.policy_name,
            scope=policy.policy_scope,
            version=policy.policy_version,
            dsl=policy.policy_dsl,
            status=policy.policy_status,
            hash=policy.policy_hash,
            immutable_hash=policy.immutable_hash
        )

    async def get_policy_by_id(self, policy_id: str) -> Optional[PolicyData]:
        result = await self.db.execute(select(DeterministicPolicy).where(DeterministicPolicy.id == policy_id))
        policy = result.scalar_one_or_none()
        if not policy:
            return None
        return self._map_policy(policy)

    async def list_policies_by_client(self, client_id: str) -> List[PolicyData]:
        from uuid import UUID
        try:
            client_uuid = UUID(client_id) if isinstance(client_id, str) else client_id
        except ValueError:
            return []
            
        result = await self.db.execute(select(DeterministicPolicy).where(DeterministicPolicy.client_id == client_uuid))
        policies = result.scalars().all()
        return [self._map_policy(p) for p in policies]

    async def list_all_policies(self) -> List[PolicyData]:
        from sqlalchemy import desc
        result = await self.db.execute(select(DeterministicPolicy).order_by(desc(DeterministicPolicy.created_at)))
        policies = result.scalars().all()
        return [self._map_policy(p) for p in policies]

    async def save_policy(self, policy: PolicyData) -> PolicyData:
        from uuid import UUID
        client_uuid = UUID(policy.client_id)
        
        db_policy = await self.db.get(DeterministicPolicy, policy.id)
        if db_policy:
            db_policy.policy_name = policy.name
            db_policy.policy_scope = policy.scope
            db_policy.policy_version = policy.version
            db_policy.policy_dsl = policy.dsl
            db_policy.policy_status = policy.status
            db_policy.policy_hash = policy.hash
        else:
            db_policy = DeterministicPolicy(
                id=policy.id,
                client_id=client_uuid,
                policy_name=policy.name,
                policy_scope=policy.scope,
                policy_version=policy.version,
                policy_dsl=policy.dsl,
                policy_status=policy.status,
                policy_hash=policy.hash,
                immutable_hash=policy.immutable_hash
            )
            self.db.add(db_policy)
            
        await self.db.flush()
        return self._map_policy(db_policy)

    async def delete_policy(self, policy_id: str) -> None:
        await self.db.execute(delete(DeterministicPolicy).where(DeterministicPolicy.id == policy_id))
        await self.db.flush()
