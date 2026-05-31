import uuid
from typing import Any
from app.models.operations.adapter_promotion import (
    AdapterPromotionWorkflow,
    AdapterPromotionGateResult,
    AdapterPromotionStageTransition,
    AdapterPromotionRollback,
    AdapterPromotionReceipt,
)
from app.services.operations.adapter_promotion.hash_utils import sha256_hex, canonical_json
from app.core.time import utc_now

def build_promotion_workflow_receipt(workflow: AdapterPromotionWorkflow) -> AdapterPromotionReceipt:
    payload = {
        "id": str(workflow.id),
        "adapter_name": workflow.adapter_name,
        "adapter_version": workflow.adapter_version,
        "target_stage": workflow.target_stage,
        "input_hash": workflow.input_hash,
    }
    payload_hash = sha256_hex(canonical_json(payload))
    # Deterministic immutable_hash
    immutable_hash = sha256_hex(f"receipt_workflow_{workflow.immutable_hash}")
    
    return AdapterPromotionReceipt(
        client_id=workflow.client_id,
        workflow_id=workflow.id,
        receipt_type="adapter_promotion_workflow",
        payload_hash=payload_hash,
        immutable_hash=immutable_hash,
        signature=f"promotion_sig_{payload_hash[:16]}",
        generated_at=utc_now()
    )

def build_gate_result_receipt(gate_result: AdapterPromotionGateResult) -> AdapterPromotionReceipt:
    payload = {
        "id": str(gate_result.id),
        "gate_name": gate_result.gate_name,
        "gate_status": gate_result.gate_status,
    }
    payload_hash = sha256_hex(canonical_json(payload))
    immutable_hash = sha256_hex(f"receipt_gate_{gate_result.immutable_hash}")
    
    return AdapterPromotionReceipt(
        client_id=gate_result.client_id,
        workflow_id=gate_result.workflow_id,
        receipt_type="adapter_promotion_gate",
        payload_hash=payload_hash,
        immutable_hash=immutable_hash,
        signature=f"gate_sig_{payload_hash[:16]}",
        generated_at=utc_now()
    )

def build_transition_receipt(transition: AdapterPromotionStageTransition) -> AdapterPromotionReceipt:
    payload = {
        "id": str(transition.id),
        "from_stage": transition.from_stage,
        "to_stage": transition.to_stage,
        "transition_status": transition.transition_status,
    }
    payload_hash = sha256_hex(canonical_json(payload))
    immutable_hash = sha256_hex(f"receipt_transition_{transition.immutable_hash}")
    
    return AdapterPromotionReceipt(
        client_id=transition.client_id,
        workflow_id=transition.workflow_id,
        receipt_type="adapter_promotion_transition",
        payload_hash=payload_hash,
        immutable_hash=immutable_hash,
        signature=f"transition_sig_{payload_hash[:16]}",
        generated_at=utc_now()
    )

def build_rollback_receipt(rollback: AdapterPromotionRollback) -> AdapterPromotionReceipt:
    payload = {
        "id": str(rollback.id),
        "from_stage": rollback.from_stage,
        "rollback_to_stage": rollback.rollback_to_stage,
        "rollback_status": rollback.rollback_status,
    }
    payload_hash = sha256_hex(canonical_json(payload))
    immutable_hash = sha256_hex(f"receipt_rollback_{rollback.immutable_hash}")
    
    return AdapterPromotionReceipt(
        client_id=rollback.client_id,
        workflow_id=rollback.workflow_id,
        receipt_type="adapter_promotion_rollback",
        payload_hash=payload_hash,
        immutable_hash=immutable_hash,
        signature=f"rollback_sig_{payload_hash[:16]}",
        generated_at=utc_now()
    )
