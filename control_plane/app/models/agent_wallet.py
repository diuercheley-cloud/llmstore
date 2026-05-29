# Owner: agent-platform
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base

class AgentWallet(Base):
    # Owner: agent-platform
    __tablename__ = "agent_wallets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, unique=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    
    currency: Mapped[str] = mapped_column(String(16), default="BRL")
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    
    provider_type: Mapped[str] = mapped_column(String(32), default="internal") # internal|stripe|web3
    provider_wallet_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    
    status: Mapped[str] = mapped_column(String(32), default="active") # active|frozen|closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentWalletLedgerEntry(Base):
    # Owner: agent-platform
    __tablename__ = "agent_wallet_ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False) # credit|debit
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    transaction_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentSpendAuthorization(Base):
    # Owner: agent-platform
    __tablename__ = "agent_spend_authorizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    
    status: Mapped[str] = mapped_column(String(32), default="pending") # pending|approved|rejected|used
    approver_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AgentWalletLimit(Base):
    # Owner: agent-platform
    __tablename__ = "agent_wallet_limits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_wallets.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    max_per_run: Mapped[float] = mapped_column(Float, default=10.0)
    max_daily: Mapped[float] = mapped_column(Float, default=100.0)
    approval_threshold: Mapped[float] = mapped_column(Float, default=50.0)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
