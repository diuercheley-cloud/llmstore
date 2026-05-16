from app.services.governance.policy_engine.policy_parser import hash_payload


def build_backup_hash(client_id: str, backup_name: str, backup_scope: str) -> str:
    return hash_payload({"client_id": client_id, "backup_name": backup_name, "backup_scope": backup_scope})

