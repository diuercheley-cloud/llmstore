# Owner: agent-platform
import uuid
from typing import Optional, Tuple

from app.models.agents.agent_wallet import AgentSpendAuthorization, AgentWalletLimit
from sqlalchemy.ext.asyncio import AsyncSession


class SpendAuthorization:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authorize(self, wallet_id: uuid.UUID, amount: float, purpose: str) -> Tuple[str, Optional[uuid.UUID]]:
        """
        Validates if a spend request is allowed based on limits and threshold.
        Returns (decision, authorization_id).
        """
        # Fetch limits
        from sqlalchemy.future import select
        stmt = select(AgentWalletLimit).where(AgentWalletLimit.wallet_id == wallet_id)
        res = await self.db.execute(stmt)
        limit = res.scalar_one_or_none()
        
        if not limit:
            # Default strict limit if none configured
            limit = AgentWalletLimit(wallet_id=wallet_id, max_per_run=1.0, approval_threshold=10.0)
            self.db.add(limit)
            await self.db.flush()

        if amount > limit.max_per_run:
            return "blocked_by_limit", None

        if amount >= limit.approval_threshold:
            auth = AgentSpendAuthorization(
                wallet_id=wallet_id,
                amount=amount,
                purpose=purpose,
                status="pending"
            )
            self.db.add(auth)
            await self.db.commit()
            await self.db.refresh(auth)
            return "require_approval", auth.id

        return "allowed", None

    async def approve(self, auth_id: uuid.UUID, approver_id: str):
        auth = await self.db.get(AgentSpendAuthorization, auth_id)
        if auth:
            auth.status = "approved"
            auth.approver_id = approver_id
            await self.db.commit()
