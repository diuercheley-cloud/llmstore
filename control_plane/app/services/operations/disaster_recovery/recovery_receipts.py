from app.services.governance.policy_engine.policy_parser import hash_payload


def build_recovery_receipt(recovery_plan_id: str, verification_status: str) -> dict:
    payload = {"recovery_plan_id": recovery_plan_id, "verification_status": verification_status}
    return {
        "receipt_type": "recovery_verification",
        "payload_hash": hash_payload(payload),
        "signature": f"recovery_receipt_{recovery_plan_id[:12]}",
    }

