from app.services.governance.policy_engine.policy_parser import hash_payload


def build_policy_receipt(policy_id: str, decision: str, subject_ref: str) -> dict:
    payload = {"policy_id": policy_id, "decision": decision, "subject_ref": subject_ref}
    return {
        "receipt_type": "deterministic_policy_evaluation",
        "payload_hash": hash_payload(payload),
        "signature": f"policy_receipt_{policy_id[:12]}",
    }
