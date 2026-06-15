from app.services.governance.policy_engine.policy_parser import hash_payload


def build_policy_audit_event(action: str, policy_id: str, status: str) -> dict:
    payload = {"action": action, "policy_id": policy_id, "status": status}
    return {"event_type": "policy_audit", "event_hash": hash_payload(payload), "payload": payload}
