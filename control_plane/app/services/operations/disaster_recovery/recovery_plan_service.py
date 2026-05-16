from app.services.governance.policy_engine.policy_parser import hash_payload


def build_recovery_hash(client_id: str, recovery_scope: str, recovery_strategy: str, dry_run: bool) -> str:
    return hash_payload(
        {
            "client_id": client_id,
            "recovery_scope": recovery_scope,
            "recovery_strategy": recovery_strategy,
            "dry_run": dry_run,
        }
    )

