from app.services.governance.policy_engine.policy_parser import hash_payload


def build_export_hash(client_id: str, export_scope: str, sanitized: bool, export_status: str) -> str:
    return hash_payload(
        {
            "client_id": client_id,
            "export_scope": export_scope,
            "sanitized": sanitized,
            "export_status": export_status,
        }
    )

