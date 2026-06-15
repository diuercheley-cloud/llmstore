import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from app.models.billing.ai_wallet import AiWallet
from app.models.core.client import Client
from app.services.billing.dispute_management import DisputeManagementService
from sqlalchemy import select


@pytest_asyncio.fixture
async def sample_client(session):
    client = Client(id=uuid.uuid4(), name="Test Dispute Client", billing_status="active")
    session.add(client)
    wallet = AiWallet(client_id=client.id, balance_brl=Decimal("100.0000"))
    session.add(wallet)
    await session.commit()
    return client


@pytest.mark.asyncio
async def test_open_dispute(session, sample_client):
    dispute = await DisputeManagementService.open_dispute(
        session,
        client_id=sample_client.id,
        dispute_type="qos_usage",
        claimed_amount_brl=Decimal("5.00"),
        disputed_reason="Overcharged for usage",
    )
    assert dispute.id is not None
    assert dispute.status == "open"
    assert dispute.client_id == sample_client.id


@pytest.mark.asyncio
async def test_resolve_dispute_with_credit(session, sample_client):
    dispute = await DisputeManagementService.open_dispute(
        session,
        client_id=sample_client.id,
        dispute_type="qos_usage",
        claimed_amount_brl=Decimal("10.00"),
        disputed_reason="Faulty usage detection",
    )

    success = await DisputeManagementService.resolve_dispute(
        session,
        dispute_id=dispute.id,
        resolution_notes="Agreed with client, issuing credit",
        credit_amount_brl=Decimal("10.00"),
    )

    assert success is True
    assert dispute.status == "credited"
    assert dispute.credit_transaction_id is not None

    # Check wallet balance increased
    stmt = select(AiWallet).where(AiWallet.client_id == sample_client.id)
    wallet = (await session.execute(stmt)).scalar_one()
    assert wallet.balance_brl == Decimal("110.0000")


@pytest.mark.asyncio
async def test_reject_dispute(session, sample_client):
    dispute = await DisputeManagementService.open_dispute(
        session,
        client_id=sample_client.id,
        dispute_type="qos_usage",
        claimed_amount_brl=Decimal("10.00"),
        disputed_reason="Invalid claim",
    )

    success = await DisputeManagementService.reject_dispute(
        session, dispute_id=dispute.id, resolution_notes="Usage was correct based on logs"
    )

    assert success is True
    assert dispute.status == "rejected"
    assert dispute.resolved_at is not None


@pytest.mark.asyncio
async def test_manual_credit_disabled(session, sample_client, settings):
    settings.commercial_financial_manual_credit_enabled = False

    with pytest.raises(ValueError, match="Manual credit is disabled"):
        await DisputeManagementService.create_manual_credit(
            session,
            client_id=sample_client.id,
            amount_brl=Decimal("50.00"),
            reason="Apology credit",
            admin_id="admin_1",
        )


@pytest.mark.asyncio
async def test_manual_credit_enabled(session, sample_client, settings):
    settings.commercial_financial_manual_credit_enabled = True

    tx = await DisputeManagementService.create_manual_credit(
        session,
        client_id=sample_client.id,
        amount_brl=Decimal("50.00"),
        reason="Apology credit",
        admin_id="admin_1",
    )

    assert tx.id is not None
    assert tx.amount_brl == Decimal("50.00")

    # Check wallet balance
    stmt = select(AiWallet).where(AiWallet.client_id == sample_client.id)
    wallet = (await session.execute(stmt)).scalar_one()
    assert wallet.balance_brl == Decimal("150.0000")
