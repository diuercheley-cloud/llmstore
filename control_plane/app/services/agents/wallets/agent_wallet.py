# Owner: agent-platform
import uuid
from typing import Any

from app.core.config import get_settings
from app.models.agents.agent_wallet import AgentWallet, AgentWalletLimit
from sqlalchemy.ext.asyncio import AsyncSession

from .spend_authorization import SpendAuthorization
from .wallet_ledger import WalletLedger


class AgentWalletService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.ledger = WalletLedger(db)
        self.authorization = SpendAuthorization(db)

    async def get_wallet(self, agent_id: uuid.UUID) -> AgentWallet | None:
        from sqlalchemy.future import select

        stmt = select(AgentWallet).where(AgentWallet.agent_id == agent_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create_wallet(
        self, agent_id: uuid.UUID, tenant_id: str, initial_balance: float = 0.0
    ) -> AgentWallet:
        wallet = AgentWallet(agent_id=agent_id, tenant_id=tenant_id, balance=initial_balance)
        self.db.add(wallet)
        await self.db.flush()

        # Default limits
        limit = AgentWalletLimit(wallet_id=wallet.id)
        self.db.add(limit)

        await self.db.commit()
        await self.db.refresh(wallet)
        return wallet

    async def spend(
        self, agent_id: uuid.UUID, amount: float, purpose: str, run_id: uuid.UUID | None = None
    ) -> dict[str, Any]:
        """
        Executes a spend transaction if authorized.
        """
        if not self.settings.agent_wallets_enabled:
            raise PermissionError("Agent wallets are disabled.")

        wallet = await self.get_wallet(agent_id)
        if not wallet:
            raise ValueError("Agent does not have a wallet.")

        # Check for external spend blocking
        # (Assuming all spend currently is internal until external providers are active)
        if (
            not self.settings.agent_wallet_external_spend_enabled
            and wallet.provider_type != "internal"
        ):
            raise PermissionError("External spend is disabled.")

        # 1. Authorize
        decision, auth_id = await self.authorization.authorize(wallet.id, amount, purpose)
        if decision == "blocked_by_limit":
            return {"status": "rejected", "reason": "Spend exceeds agent limits."}
        if decision == "require_approval":
            return {"status": "pending_approval", "authorization_id": str(auth_id)}

        # 2. Record in Ledger
        entry = await self.ledger.record_transaction(
            wallet.id, "debit", amount, purpose, run_id=run_id
        )

        return {"status": "success", "transaction_id": str(entry.id), "new_balance": wallet.balance}
