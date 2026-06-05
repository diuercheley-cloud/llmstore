import uuid

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.models.agent_wallet import AgentWallet, AgentWalletLedgerEntry, AgentWalletLimit
from app.models.agents import AgentDefinition
from app.services.agents.wallets.agent_wallet import AgentWalletService


@pytest.fixture
def agent_id():
    return uuid.uuid4()

@pytest_asyncio.fixture
async def setup_agent_wallet(session, agent_id):
    agent = AgentDefinition(
        id=agent_id,
        name="Wealthy Agent",
        version="1.0",
        model_id="test",
        owner="test",
        tenant_id="t1",
        instructions="test"
    )
    session.add(agent)
    
    service = AgentWalletService(session)
    wallet = await service.create_wallet(agent_id, "t1", initial_balance=100.0)
    return wallet

@pytest.mark.asyncio
async def test_wallet_disabled_bloqueia(session, setup_agent_wallet, agent_id):
    settings = get_settings()
    settings.agent_wallets_enabled = False
    
    service = AgentWalletService(session)
    with pytest.raises(PermissionError, match="wallets are disabled"):
        await service.spend(agent_id, 10.0, "test")

@pytest.mark.asyncio
async def test_budget_excedido_bloqueia(session, setup_agent_wallet, agent_id):
    settings = get_settings()
    settings.agent_wallets_enabled = True
    
    service = AgentWalletService(session)
    # Default limit is 10.0 per run
    res = await service.spend(agent_id, 15.0, "expensive purchase")
    assert res["status"] == "rejected"
    assert "exceeds agent limits" in res["reason"]

@pytest.mark.asyncio
async def test_ledger_registra_debito_credito(session, setup_agent_wallet, agent_id):
    settings = get_settings()
    settings.agent_wallets_enabled = True
    
    service = AgentWalletService(session)
    res = await service.spend(agent_id, 5.0, "small snack")
    assert res["status"] == "success"
    
    wallet = await service.get_wallet(agent_id)
    assert wallet.balance == 95.0
    
    # Check ledger
    from sqlalchemy.future import select
    stmt = select(AgentWalletLedgerEntry).where(AgentWalletLedgerEntry.wallet_id == wallet.id)
    entries = list((await session.execute(stmt)).scalars().all())
    assert len(entries) == 1
    assert entries[0].amount == 5.0
    assert entries[0].entry_type == "debit"

@pytest.mark.asyncio
async def test_high_spend_exige_approval(session, setup_agent_wallet, agent_id):
    settings = get_settings()
    settings.agent_wallets_enabled = True
    
    # Set limit high but threshold low
    from sqlalchemy.future import select
    stmt = select(AgentWalletLimit).where(AgentWalletLimit.wallet_id == setup_agent_wallet.id)
    res = await session.execute(stmt)
    limit = res.scalar_one()
    
    limit.max_per_run = 100.0
    limit.approval_threshold = 50.0
    await session.commit()
    
    service = AgentWalletService(session)
    res = await service.spend(agent_id, 75.0, "major investment")
    assert res["status"] == "pending_approval"
    assert "authorization_id" in res

@pytest.mark.asyncio
async def test_external_spend_bloqueado_por_default(session, agent_id):
    settings = get_settings()
    settings.agent_wallets_enabled = True
    settings.agent_wallet_external_spend_enabled = False
    
    # Create a wallet with external provider type
    agent = AgentDefinition(id=agent_id, name="Ext", version="1", model_id="m", owner="o", tenant_id="t", instructions="i")
    session.add(agent)
    wallet = AgentWallet(agent_id=agent_id, tenant_id="t", balance=100.0, provider_type="stripe")
    session.add(wallet)
    await session.commit()
    
    service = AgentWalletService(session)
    with pytest.raises(PermissionError, match="External spend is disabled"):
        await service.spend(agent_id, 10.0, "stripe payment")
