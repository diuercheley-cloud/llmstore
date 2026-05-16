from app.services.governance.policy_engine.policy_parser import hash_payload


def build_escalation_hash(client_id: str, workflow_id: str, escalation_reason: str, escalation_status: str) -> str:
    return hash_payload(
        {
            "client_id": client_id,
            "workflow_id": workflow_id,
            "escalation_reason": escalation_reason,
            "escalation_status": escalation_status,
        }
    )

