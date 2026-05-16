from app.services.governance.policy_engine.policy_parser import hash_payload


def build_zone_hash(client_id: str, zone_name: str, zone_scope: str, export_allowed: bool, retention_policy: str) -> str:
    return hash_payload(
        {
            "client_id": client_id,
            "zone_name": zone_name,
            "zone_scope": zone_scope,
            "export_allowed": export_allowed,
            "retention_policy": retention_policy,
        }
    )

