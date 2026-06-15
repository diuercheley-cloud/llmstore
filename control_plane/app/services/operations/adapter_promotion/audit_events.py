from typing import Any

from app.core.time import utc_now
from app.models.operations.adapter_promotion import AdapterPromotionWorkflow
from app.services.operations.adapter_promotion.hash_utils import sha256_hex


def build_promotion_audit_event(
    event_type: str, workflow: AdapterPromotionWorkflow, details: dict[str, Any]
) -> dict[str, Any]:
    """Builds a standardized audit event for adapter promotion."""
    payload = {
        "event_type": event_type,
        "client_id": str(workflow.client_id),
        "workflow_id": str(workflow.id),
        "adapter_name": workflow.adapter_name,
        "adapter_version": workflow.adapter_version,
        "details": details,
        "timestamp": utc_now().isoformat(),
    }
    return {
        "event_type": event_type,
        "client_id": workflow.client_id,
        "payload": payload,
        "immutable_hash": sha256_hex(
            f"audit_promotion_{event_type}_{workflow.id}_{utc_now().isoformat()}"
        ),
    }
