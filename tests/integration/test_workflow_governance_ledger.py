from __future__ import annotations

import pytest
from app.models.commercial.commercial_governance import CommercialPolicyBundle
from app.models.commercial.commercial_workflows import CommercialWorkflowGovernanceEvent
from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator
from app.services.workflows.workflow_governance_ledger import WorkflowGovernanceLedgerService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_immutable_governance_ledger_validates(session: AsyncSession):
    bundle = CommercialPolicyBundle(
        bundle_name="ledger-policy",
        bundle_version="1",
        bundle_type="workflow",
        mode="enforce",
        status="active",
        rules_json={"allow": True},
        metadata_json={},
        immutable_hash="ledger-policy-hash",
    )
    session.add(bundle)
    await session.flush()
    orchestrator = DeterministicWorkflowOrchestrator()
    definition = await orchestrator.create_definition(
        session,
        name="ledger-workflow",
        dag_or_steps=[
            {"stage_key": "stage-a", "policy": {"bundle_ref": str(bundle.id)}, "config": {"x": 1}}
        ],
    )
    execution = await orchestrator.start_execution(
        session, definition_id=definition.id, session_id="ledger-session", tenant_id="tenant-a"
    )

    validation = await WorkflowGovernanceLedgerService().validate_ledger(
        session, execution_id=execution.id
    )

    assert validation["valid"] is True
    assert validation["count"] >= 2


@pytest.mark.asyncio
async def test_immutable_governance_ledger_detects_tampering(session: AsyncSession):
    bundle = CommercialPolicyBundle(
        bundle_name="ledger-policy-2",
        bundle_version="1",
        bundle_type="workflow",
        mode="enforce",
        status="active",
        rules_json={"allow": True},
        metadata_json={},
        immutable_hash="ledger-policy-hash-2",
    )
    session.add(bundle)
    await session.flush()
    orchestrator = DeterministicWorkflowOrchestrator()
    definition = await orchestrator.create_definition(
        session,
        name="ledger-workflow-2",
        dag_or_steps=[
            {"stage_key": "stage-a", "policy": {"bundle_ref": str(bundle.id)}, "config": {"x": 1}}
        ],
    )
    execution = await orchestrator.start_execution(
        session, definition_id=definition.id, session_id="ledger-session-2", tenant_id="tenant-a"
    )
    row = (
        await session.execute(
            select(CommercialWorkflowGovernanceEvent)
            .where(CommercialWorkflowGovernanceEvent.execution_id == execution.id)
            .limit(1)
        )
    ).scalar_one()
    row.ledger_hash = "tampered"

    validation = await WorkflowGovernanceLedgerService().validate_ledger(
        session, execution_id=execution.id
    )

    assert validation["valid"] is False
    assert any("ledger_hash_invalid" in issue for issue in validation["issues"])
