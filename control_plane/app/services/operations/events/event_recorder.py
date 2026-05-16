from app.services.governance.policy_engine.policy_parser import hash_payload


def build_event_hash(client_id: str, event_name: str, event_version: str, subject_type: str, subject_ref: str, previous_event_hash: str | None) -> str:
    return hash_payload(
        {
            "client_id": client_id,
            "event_name": event_name,
            "event_version": event_version,
            "subject_type": subject_type,
            "subject_ref": subject_ref,
            "previous_event_hash": previous_event_hash,
        }
    )

