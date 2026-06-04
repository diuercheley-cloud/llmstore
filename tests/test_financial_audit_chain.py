from decimal import Decimal

import pytest
from app.models.commercial_financial_audit_event import CommercialFinancialAuditEvent
from app.services.billing.financial_audit_trail import FinancialAuditTrailService


@pytest.mark.asyncio
async def test_audit_hash_chain(session):
    # Create first event
    event1 = await FinancialAuditTrailService.create_audit_event(
        session,
        event_type="qos_billing_created",
        amount_brl=Decimal("10.00")
    )
    await session.flush()
    
    # Create second event
    event2 = await FinancialAuditTrailService.create_audit_event(
        session,
        event_type="qos_wallet_debited",
        amount_brl=Decimal("10.00")
    )
    await session.commit()
    
    # Validate chain
    is_valid = await FinancialAuditTrailService.validate_audit_chain(session)
    assert is_valid is True
    
    # Check that hashes are different
    assert event1.immutable_hash != event2.immutable_hash
    assert event1.immutable_hash != "0" * 64


@pytest.mark.asyncio
async def test_audit_chain_tamper_detection(session):
    # Create events
    await FinancialAuditTrailService.create_audit_event(
        session,
        event_type="event_1",
        amount_brl=Decimal("1.00")
    )
    await session.flush()
    
    event2 = await FinancialAuditTrailService.create_audit_event(
        session,
        event_type="event_2",
        amount_brl=Decimal("2.00")
    )
    await session.commit()
    
    # Manually tamper with an event
    from sqlalchemy import update
    await session.execute(
        update(CommercialFinancialAuditEvent)
        .where(CommercialFinancialAuditEvent.id == event2.id)
        .values(amount_brl=Decimal("999.00"))
    )
    await session.commit()
    
    # Validate chain should fail
    is_valid = await FinancialAuditTrailService.validate_audit_chain(session)
    assert is_valid is False
