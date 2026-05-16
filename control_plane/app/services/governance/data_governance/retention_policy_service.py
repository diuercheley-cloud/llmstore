from app.services.governance.policy_engine.policy_parser import hash_payload


def build_retention_hash(client_id: str, rule_name: str, retention_scope: str, retention_days: int, enforcement_mode: str) -> str:
    return hash_payload(
        {
            "client_id": client_id,
            "rule_name": rule_name,
            "retention_scope": retention_scope,
            "retention_days": retention_days,
            "enforcement_mode": enforcement_mode,
        }
    )

