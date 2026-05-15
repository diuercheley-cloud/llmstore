from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.models.commercial_compliance import CommercialControlPolicy
from app.services.compliance.financial_controls import (
    ControlViolationError,
    approve_action,
    evaluate_control_policy,
)


@pytest.fixture(autouse=True)
def compliance_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_COMPLIANCE_CONTROLS_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_COMPLIANCE_MODE", "enforce")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_segregation_blocks_self_approval(session):
    policy = CommercialControlPolicy(
        name="Manual credit approval",
        control_area="billing",
        action_type="manual_credit",
        requires_approval=True,
        required_approver_count=1,
        segregation_required=True,
    )
    session.add(policy)
    await session.commit()

    decision = await evaluate_control_policy(
        session,
        control_area="billing",
        action_type="manual_credit",
        target_type="Client",
        target_id="client-1",
        actor="same-user",
        summary="Manual credit",
    )
    await session.commit()

    assert decision.should_block is True
    with pytest.raises(ControlViolationError):
        await approve_action(session, chain_id=decision.approval_chain.id, approver="same-user")


@pytest.mark.asyncio
async def test_multi_approver_chain_requires_all_approvals(session):
    policy = CommercialControlPolicy(
        name="Infra execution approval",
        control_area="infra_execution",
        action_type="real_execution",
        requires_approval=True,
        required_approver_count=2,
        segregation_required=True,
    )
    session.add(policy)
    await session.commit()

    decision = await evaluate_control_policy(
        session,
        control_area="infra_execution",
        action_type="real_execution",
        target_type="CommercialInfrastructureSimulation",
        target_id="sim-1",
        actor="requester",
        summary="Infra execution",
    )

    chain = await approve_action(session, chain_id=decision.approval_chain.id, approver="approver-1")
    assert chain.status == "pending"
    chain = await approve_action(session, chain_id=decision.approval_chain.id, approver="approver-2")
    assert chain.status == "approved"
