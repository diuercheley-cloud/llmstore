from app.services.governance.policy_engine.policy_parser import hash_payload


def build_recovery_audit_event(action: str, recovery_plan_id: str, status: str) -> dict:
    payload = {"action": action, "recovery_plan_id": recovery_plan_id, "status": status}
    return {"event_type": "recovery_audit", "event_hash": hash_payload(payload), "payload": payload}
