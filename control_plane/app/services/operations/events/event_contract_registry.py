from app.services.governance.policy_engine.policy_parser import hash_payload


def build_contract_hash(event_name: str, event_version: str, event_scope: str, schema: dict) -> str:
    return hash_payload(
        {
            "event_name": event_name,
            "event_version": event_version,
            "event_scope": event_scope,
            "schema": schema,
        }
    )
