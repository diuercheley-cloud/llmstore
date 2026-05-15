import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy import select
from app.models.commercial_qos_billing_record import CommercialQoSBillingRecord
from app.models.commercial_queue_chargeback import CommercialQueueChargeback
from app.models.ai_wallet import AiWallet, AiWalletTransaction
from app.models.billing_invoice import BillingInvoice
from app.models.client import Client
from app.models.commercial_financial_reconciliation import CommercialFinancialReconciliation
from app.services.billing.financial_reconciliation import FinancialReconciliationService
from app.core.time import utc_now


@pytest.fixture
async def sample_client(session):
    client = Client(
        id=uuid.uuid4(),
        name="Test Reconciliation Client",
        billing_status="active"
    )
    session.add(client)
    wallet = AiWallet(client_id=client.id, balance_brl=Decimal("100.0000"))
    session.add(wallet)
    await session.commit()
    return client


@pytest.mark.asyncio
async def test_reconcile_qos_billing_matched(session, sample_client, settings):
    settings.commercial_qos_billing_include_opportunity_cost = False
    
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
        chargeback_amount_brl=Decimal("1.000000")
    )
    session.add(cb)
    await session.flush()
    
    record = CommercialQoSBillingRecord(
        client_id=sample_client.id,
        qos_tier="Premium",
        model="gpt-4",
        period_start=cb.period_start,
        period_end=cb.period_end,
        chargeback_id=cb.id,
        billable_amount_brl=Decimal("1.000000"),
        billing_mode="report_only",
        status="calculated",
        idempotency_key=str(uuid.uuid4()),
        created_at=utc_now()
    )
    session.add(record)
    await session.commit()
    
    recons = await FinancialReconciliationService.reconcile_qos_billing(
        session, utc_now() - timedelta(hours=24), utc_now() + timedelta(hours=1)
    )
    assert len(recons) == 0 # No mismatches


@pytest.mark.asyncio
async def test_reconcile_qos_billing_mismatch(session, sample_client, settings):
    settings.commercial_qos_billing_include_opportunity_cost = False
    settings.commercial_financial_reconciliation_threshold_percent = 2.0
    
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
        chargeback_amount_brl=Decimal("1.000000")
    )
    session.add(cb)
    await session.flush()
    
    # Intentionally create mismatch: billable_amount_brl is 1.5 but CB says 1.0
    record = CommercialQoSBillingRecord(
        client_id=sample_client.id,
        qos_tier="Premium",
        model="gpt-4",
        period_start=cb.period_start,
        period_end=cb.period_end,
        chargeback_id=cb.id,
        billable_amount_brl=Decimal("1.500000"),
        billing_mode="report_only",
        status="calculated",
        idempotency_key=str(uuid.uuid4()),
        created_at=utc_now()
    )
    session.add(record)
    await session.commit()
    
    recons = await FinancialReconciliationService.reconcile_qos_billing(
        session, utc_now() - timedelta(hours=24), utc_now() + timedelta(hours=1)
    )
    assert len(recons) == 1
    assert recons[0].status == "mismatch"
    assert recons[0].actual_amount_brl == Decimal("1.500000")
    assert recons[0].expected_amount_brl == Decimal("1.000000")


@pytest.mark.asyncio
async def test_reconcile_wallet_debits_mismatch(session, sample_client, settings):
    record = CommercialQoSBillingRecord(
        client_id=sample_client.id,
        qos_tier="Premium",
        period_start=utc_now() - timedelta(hours=1),
        period_end=utc_now(),
        billable_amount_brl=Decimal("10.000000"),
        billing_mode="wallet_debit_opt_in",
        status="debited",
        idempotency_key=str(uuid.uuid4()),
        created_at=utc_now() - timedelta(minutes=10),
        processed_at=utc_now() - timedelta(minutes=5)
    )
    session.add(record)
    await session.flush()
    
    # Transaction missing
    recons = await FinancialReconciliationService.reconcile_wallet_debits(
        session, utc_now() - timedelta(hours=24), utc_now() + timedelta(hours=1)
    )
    assert len(recons) == 1
    assert recons[0].reconciliation_type == "wallet"
    assert recons[0].status == "mismatch"
    assert "wallet_transaction_id is null" in recons[0].notes


@pytest.mark.asyncio
async def test_summarize_reconciliation(session, sample_client):
    recon = CommercialFinancialReconciliation(
        reconciliation_type="qos_billing",
        status="mismatch",
        expected_amount_brl=Decimal("100"),
        actual_amount_brl=Decimal("110"),
        delta_amount_brl=Decimal("10"),
        period_start=utc_now(),
        period_end=utc_now()
    )
    session.add(recon)
    await session.commit()
    
    summary = await FinancialReconciliationService.summarize_reconciliation(session)
    assert "mismatch" in summary
    assert summary["mismatch"]["count"] == 1
    assert summary["mismatch"]["total_delta"] == 10.0
