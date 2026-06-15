from app.services.operations.disaster_recovery.recovery_plan_service import build_recovery_hash


def verify_recovery_replay(payload: dict, expected_hash: str) -> dict:
    actual_hash = build_recovery_hash(
        payload["client_id"],
        payload["recovery_scope"],
        payload["recovery_strategy"],
        payload["dry_run"],
    )
    return {
        "verification_status": "passed" if actual_hash == expected_hash else "failed",
        "replay_safe": actual_hash == expected_hash,
    }
