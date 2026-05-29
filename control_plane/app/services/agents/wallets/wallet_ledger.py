# Owner: agent-platform
import uuid
import hashlib
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.agent_wallet import AgentWalletLedgerEntry, AgentWallet

class WalletLedger:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_transaction(
        self, 
        wallet_id: uuid.UUID, 
        entry_type: str, 
        amount: float, 
        description: str,
        run_id: uuid.UUID = None
    ) -> AgentWalletLedgerEntry:
        """
        Records an immutable ledger entry and updates the wallet balance.
        """
        # Update wallet balance
        wallet = await self.db.get(AgentWallet, wallet_id)
        if not wallet:
            raise ValueError("Wallet not found")

        if entry_type == "debit":
            if wallet.balance < amount:
                raise ValueError("Insufficient balance in agent wallet")
            wallet.balance -= amount
        elif entry_type == "credit":
            wallet.balance += amount
        else:
            raise ValueError(f"Invalid entry type: {entry_type}")

        # Create ledger entry
        # Simple transaction hash for "immutability" mock
        tx_content = f"{wallet_id}:{entry_type}:{amount}:{description}"
        tx_hash = hashlib.sha256(tx_content.encode()).hexdigest()

        entry = AgentWalletLedgerEntry(
            wallet_id=wallet_id,
            entry_type=entry_type,
            amount=amount,
            description=description,
            run_id=run_id,
            transaction_hash=tx_hash
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def list_entries(self, wallet_id: uuid.UUID) -> List[AgentWalletLedgerEntry]:
        stmt = select(AgentWalletLedgerEntry).where(AgentWalletLedgerEntry.wallet_id == wallet_id).order_by(AgentWalletLedgerEntry.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
