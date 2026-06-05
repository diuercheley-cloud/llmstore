import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from app.core.time import utc_now
from app.models.ai_wallet import AiWallet
from app.models.billing_invoice import BillingInvoice
from app.models.client import Client
from app.models.commercial_queue_chargeback import CommercialQueueChargeback
from app.services.billing.qos_billing import CommercialQoSBillingService
from sqlalchemy import select


@pytest_asyncio.fixture
async def sample_client(session):
    client = Client(
        id=uuid.uuid4(),
        name="Test QoS Client",
        billing_status="active"
    )
    session.add(client)
    wallet = AiWallet(client_id=client.id, balance_brl=Decimal("100.0000"))
    session.add(wallet)
    await session.commit()
    return client

@pytest_asyncio.fixture
async def sample_chargeback(session, sample_client):
    cb = CommercialQueueChargeback(
        client_id=sample_client.id,
        qos_tier="Premium",
        model="gpt-4",
        period_start=utc_now() - timedelta(hours=1),
        period_end=utc_now(),
        compute_seconds=100.0,
        priority_slots_consumed=10.0,
        estimated_internal_cost_brl=Decimal("1.000000"),
        estimated_opportunity_cost_brl=Decimal("0.500000"),
        chargeback_amount_brl=Decimal("1.500000")
    )
    session.add(cb)
    await session.commit()
    return cb

@pytest.mark.asyncio
async def test_generate_qos_billing_records_report_only(session, sample_chargeback, settings):
    settings.commercial_qos_billing_enabled = True
    settings.commercial_qos_billing_mode = "report_only"
    
    records = await CommercialQoSBillingService.generate_qos_billing_records(session)
    assert len(records) == 1
    record = records[0]
    assert record.billable_amount_brl == Decimal("1.000000") # Default: no opportunity cost
    assert record.status == "calculated"
    assert record.billing_mode == "report_only"

@pytest.mark.asyncio
async def test_generate_qos_billing_include_opportunity_cost(session, sample_chargeback, settings):
    settings.commercial_qos_billing_enabled = True
    settings.commercial_qos_billing_mode = "report_only"
    settings.commercial_qos_billing_include_opportunity_cost = True
    
    records = await CommercialQoSBillingService.generate_qos_billing_records(session)
    assert len(records) == 1
    assert records[0].billable_amount_brl == Decimal("1.500000")

@pytest.mark.asyncio
async def test_generate_qos_billing_idempotency(session, sample_chargeback, settings):
    settings.commercial_qos_billing_enabled = True
    
    records1 = await CommercialQoSBillingService.generate_qos_billing_records(session)
    assert len(records1) == 1
    
    records2 = await CommercialQoSBillingService.generate_qos_billing_records(session)
    assert len(records2) == 0

@pytest.mark.asyncio
async def test_debit_wallet_opt_in(session, sample_client, sample_chargeback, settings):
    settings.commercial_qos_billing_enabled = True
    settings.commercial_qos_billing_mode = "wallet_debit_opt_in"
    settings.commercial_qos_billing_debit_wallet = True
    
    records = await CommercialQoSBillingService.generate_qos_billing_records(session)
    record = records[0]
    
    tx = await CommercialQoSBillingService.debit_wallet_for_qos(session, record)
    assert tx is not None
    assert record.status == "debited"
    assert record.wallet_transaction_id == tx.id
    
    # Check wallet balance
    stmt = select(AiWallet).where(AiWallet.client_id == sample_client.id)
    wallet = (await session.execute(stmt)).scalar_one()
    assert wallet.balance_brl == Decimal("99.0000") # 100 - 1

@pytest.mark.asyncio
async def test_debit_wallet_blocked_without_opt_in(session, sample_client, sample_chargeback, settings):
    settings.commercial_qos_billing_enabled = True
    settings.commercial_qos_billing_mode = "report_only"
    settings.commercial_qos_billing_debit_wallet = True # But mode is report_only
    
    records = await CommercialQoSBillingService.generate_qos_billing_records(session)
    record = records[0]
    
    tx = await CommercialQoSBillingService.debit_wallet_for_qos(session, record)
    assert tx is None
    assert record.status == "skipped"

@pytest.mark.asyncio
async def test_attach_to_invoice(session, sample_client, sample_chargeback, settings):
    settings.commercial_qos_billing_enabled = True
    settings.commercial_qos_billing_mode = "invoice_line_item"
    
    invoice = BillingInvoice(
        client_id=sample_client.id,
        status="pending",
        currency="BRL",
        period_start=utc_now().date(),
        period_end=utc_now().date(),
        monthly_price=Decimal("0"),
        included_tokens=0,
        used_tokens=0,
        overage_tokens=0,
        overage_price_per_1k_tokens=Decimal("0"),
        overage_cost=Decimal("0"),
        total_amount=Decimal("10.000000")
    )
    session.add(invoice)
    await session.commit()
    
    records = await CommercialQoSBillingService.generate_qos_billing_records(session)
    record = records[0]
    
    success = await CommercialQoSBillingService.attach_to_invoice(session, record, invoice.id)
    assert success is True
    assert record.status == "invoiced"
    assert record.invoice_id == invoice.id
    assert invoice.total_amount == Decimal("11.000000")

@pytest.mark.asyncio
async def test_daily_limit(session, sample_client, sample_chargeback, settings):
    settings.commercial_qos_billing_enabled = True
    settings.commercial_qos_billing_mode = "wallet_debit_opt_in"
    settings.commercial_qos_billing_debit_wallet = True
    settings.commercial_qos_billing_max_daily_debit_brl_per_client = 0.5 # Low limit
    
    records = await CommercialQoSBillingService.generate_qos_billing_records(session)
    record = records[0]
    
    tx = await CommercialQoSBillingService.debit_wallet_for_qos(session, record)
    assert tx is None
    assert record.status == "failed"
    assert "Daily limit exceeded" in record.error_message

@pytest.mark.asyncio
async def test_min_amount_skip(session, sample_client, sample_chargeback, settings):
    settings.commercial_qos_billing_enabled = True
    settings.commercial_qos_billing_min_amount_brl = 5.0 # High min amount
    
    records = await CommercialQoSBillingService.generate_qos_billing_records(session)
    record = records[0]
    assert record.status == "skipped"
    assert "below minimum" in record.error_message
