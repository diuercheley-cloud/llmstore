import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.operations.adapter_registry import SignedAdapterRegistryEntry
from app.services.operations.adapter_promotion.workflow_service import AdapterPromotionWorkflowService

@pytest.mark.asyncio
async def test_workflow_service_lifecycle(session: AsyncSession):
    client_id = uuid.uuid4()
    entry = SignedAdapterRegistryEntry(
        id=uuid.uuid4(),
        client_id=client_id,
        adapter_name="test",
        adapter_version="1.0.0",
        adapter_type="remediation",
        manifest_id=uuid.uuid4(),
        manifest_hash="mhash",
        registry_status="approved",
        registry_hash="rhash",
        signature="sig",
        immutable_hash="entry_imm"
    )
    session.add(entry)
    await session.flush()
    
    service = AdapterPromotionWorkflowService(session)
    workflow = await service.create_workflow(entry, "production_eligible")
    assert workflow.promotion_status == "pending"
    
    # Record gates (all pass)
    gates = [{"gate_name": "g1", "gate_status": "passed", "blocking": True}]
    await service.record_gate_results(workflow, gates)
    assert workflow.promotion_status == "pending" # status only changes to blocked if failed
    
    # Propose transition
    transition = await service.propose_transition(workflow, "staging_simulated")
    assert transition.transition_status == "proposed"
    
    # Promote
    await service.promote(workflow, transition)
    assert workflow.current_stage == "staging_simulated"
    assert workflow.promotion_status == "approved"
    assert transition.transition_status == "completed"
    
    # Promote to final target
    transition2 = await service.propose_transition(workflow, "production_eligible")
    await service.promote(workflow, transition2)
    assert workflow.current_stage == "production_eligible"
    assert workflow.promotion_status == "promoted"
    
    # Rollback
    await service.rollback(workflow, "staging_simulated", reason="security patch needed")
    assert workflow.current_stage == "staging_simulated"
    assert workflow.promotion_status == "rolled_back"
