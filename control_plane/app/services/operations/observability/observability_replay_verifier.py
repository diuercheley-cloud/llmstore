from app.services.operations.observability.metric_recorder import build_metric_hash


def verify_metric_replay(payload: dict, expected_hash: str) -> dict:
    actual_hash = build_metric_hash(
        payload["client_id"],
        payload["metric_name"],
        payload["metric_scope"],
        payload["metric_value"],
    )
    return {"verification_status": "passed" if actual_hash == expected_hash else "failed", "replay_safe": actual_hash == expected_hash}

