import uuid

from app.models.operations.adapter_promotion import AdapterPromotionWorkflow
from app.services.operations.adapter_promotion.audit_events import build_promotion_audit_event


def test_audit_event_generation():
    workflow = AdapterPromotionWorkflow(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        adapter_name="test",
        adapter_version="1.0.0"
    )
    event = build_promotion_audit_event("adapter_promoted", workflow, {"stage": "prod"})
    assert event["event_type"] == "adapter_promoted"
    assert event["client_id"] == workflow.client_id
    assert "workflow_id" in event["payload"]
    assert len(event["immutable_hash"]) == 64
