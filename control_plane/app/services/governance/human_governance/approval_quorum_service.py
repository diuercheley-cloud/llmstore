import json

from app.services.governance.policy_engine.policy_parser import hash_payload


def normalize_roles(required_roles: list[str]) -> str:
    return json.dumps(sorted(set(required_roles)))


def build_quorum_hash(client_id: str, workflow_id: str, required_roles_json: str, quorum_threshold: int) -> str:
    return hash_payload(
        {
            "client_id": client_id,
            "workflow_id": workflow_id,
            "required_roles_json": required_roles_json,
            "quorum_threshold": quorum_threshold,
        }
    )

