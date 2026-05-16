import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations.adapter_promotion import (
    AdapterPromotionWorkflow,
    AdapterPromotionGateResult,
    AdapterPromotionStageTransition,
    AdapterPromotionRollback,
)
from app.models.operations.adapter_registry import SignedAdapterRegistryEntry
from app.services.operations.adapter_promotion.hash_utils import (
    sha256_hex, 
    compute_promotion_hash, 
    compute_gate_hash, 
    compute_transition_hash
)
from app.core.time import utc_now

class AdapterPromotionWorkflowService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_workflow(
        self, 
        registry_entry: SignedAdapterRegistryEntry, 
        target_stage: str
    ) -> AdapterPromotionWorkflow:
        payload = {
            "client_id": str(registry_entry.client_id),
            "registry_entry_id": str(registry_entry.id),
            "adapter_name": registry_entry.adapter_name,
            "adapter_version": registry_entry.adapter_version,
            "target_stage": target_stage,
        }
        input_hash = compute_promotion_hash(payload)
        immutable_hash = sha256_hex(f"promotion_{input_hash}")
        
        workflow = AdapterPromotionWorkflow(
            client_id=registry_entry.client_id,
            registry_entry_id=registry_entry.id,
            adapter_name=registry_entry.adapter_name,
            adapter_version=registry_entry.adapter_version,
            current_stage="draft",
            target_stage=target_stage,
            promotion_status="pending",
            input_hash=input_hash,
            immutable_hash=immutable_hash,
        )
        self.session.add(workflow)
        await self.session.flush()
        return workflow

    async def record_gate_results(
        self, 
        workflow: AdapterPromotionWorkflow, 
        gate_results: List[Dict[str, Any]]
    ) -> List[AdapterPromotionGateResult]:
        results = []
        for gr in gate_results:
            immutable_hash = compute_gate_hash({
                "workflow_id": str(workflow.id),
                "gate_name": gr["gate_name"],
                "gate_status": gr["gate_status"]
            })
            res = AdapterPromotionGateResult(
                client_id=workflow.client_id,
                workflow_id=workflow.id,
                gate_name=gr["gate_name"],
                gate_status=gr["gate_status"],
                reason=gr.get("reason"),
                required=gr.get("required", True),
                blocking=gr.get("blocking", True),
                immutable_hash=immutable_hash
            )
            self.session.add(res)
            results.append(res)
        
        # Check if any blocking gate failed
        if any(gr["gate_status"] == "failed" and gr.get("blocking", True) for gr in gate_results):
            workflow.promotion_status = "blocked"
            
        await self.session.flush()
        return results

    async def propose_transition(self, workflow: AdapterPromotionWorkflow, to_stage: str, reason: str = None) -> AdapterPromotionStageTransition:
        immutable_hash = compute_transition_hash({
            "workflow_id": str(workflow.id),
            "from_stage": workflow.current_stage,
            "to_stage": to_stage,
            "status": "proposed"
        })
        transition = AdapterPromotionStageTransition(
            client_id=workflow.client_id,
            workflow_id=workflow.id,
            from_stage=workflow.current_stage,
            to_stage=to_stage,
            transition_status="proposed",
            reason=reason,
            immutable_hash=immutable_hash
        )
        self.session.add(transition)
        await self.session.flush()
        return transition

    async def promote(self, workflow: AdapterPromotionWorkflow, transition: AdapterPromotionStageTransition) -> None:
        if workflow.promotion_status == "blocked":
            raise ValueError("Workflow is blocked by gates and cannot be promoted")
        
        workflow.current_stage = transition.to_stage
        workflow.promotion_status = "promoted" if transition.to_stage == workflow.target_stage else "approved"
        transition.transition_status = "completed"
        await self.session.flush()

    async def rollback(self, workflow: AdapterPromotionWorkflow, rollback_to_stage: str, reason: str) -> AdapterPromotionRollback:
        if not reason:
            raise ValueError("Reason is mandatory for rollback")
            
        immutable_hash = sha256_hex(f"rollback_{workflow.id}_{workflow.current_stage}_{rollback_to_stage}")
        
        rollback = AdapterPromotionRollback(
            client_id=workflow.client_id,
            workflow_id=workflow.id,
            from_stage=workflow.current_stage,
            rollback_to_stage=rollback_to_stage,
            reason=reason,
            rollback_status="completed",
            immutable_hash=immutable_hash
        )
        
        workflow.current_stage = rollback_to_stage
        workflow.promotion_status = "rolled_back"
        
        self.session.add(rollback)
        await self.session.flush()
        return rollback

    async def explain_workflow(self, workflow: AdapterPromotionWorkflow) -> str:
        return f"Workflow {workflow.id}: {workflow.current_stage} -> {workflow.target_stage} ({workflow.promotion_status})"
