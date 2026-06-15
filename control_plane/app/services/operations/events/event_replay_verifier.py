from app.services.operations.events.event_recorder import build_event_hash


def verify_event_replay(payload: dict, expected_hash: str) -> dict:
    actual_hash = build_event_hash(
        payload["client_id"],
        payload["event_name"],
        payload["event_version"],
        payload["subject_type"],
        payload["subject_ref"],
        payload.get("previous_event_hash"),
    )
    return {
        "verification_status": "passed" if actual_hash == expected_hash else "failed",
        "replay_safe": actual_hash == expected_hash,
    }
